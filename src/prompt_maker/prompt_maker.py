import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pathspec
import pyperclip

from src.settings import (
    DATA_PATH,
    DATE,
    HISTORY_PATH,
    PROJECT_PATH,
    PYTHON_NOTEBOOKS_PATH,
)

logger = logging.getLogger("rock_info")


@dataclass
class PromptMaker:
    """Handles prompt context generation."""

    def get_prompt_context(
        self,
        target_directory: str = "Python/",
        exclude_paths: List[str] | None = None,
        file_types: List[str] | None = None,
    ) -> None:
        target_directory = Path(target_directory).resolve()
        exclude_paths = self._normalize_exclude_paths(exclude_paths)
        file_types = self._normalize_file_types(file_types)

        filename = self._generate_filename(target_directory, file_types)
        notebooks_dirs = self._get_notebooks_dirs(target_directory)
        ignore_patterns = self._load_gitignore_patterns(PROJECT_PATH)

        notebook_files = {}
        if ".ipynb" in file_types:
            notebook_files = self._process_notebooks(notebooks_dirs, ignore_patterns)
        logger.debug(f"Notebook files: {notebook_files}")

        file_paths = self._get_files(target_directory, ignore_patterns, file_types, exclude_paths)
        logger.debug(f"File paths: {file_paths}")

        output_file_path = DATA_PATH / filename
        logger.debug(f"Output file path: {output_file_path}")
        self._write_files_to_txt(file_paths, output_file_path, target_directory, notebook_files)
        self._copy_to_clipboard(output_file_path)
        self._save_historical_version(filename, output_file_path)

        logger.info(
            f"All specified files have been written to {output_file_path} and copied to the clipboard."
        )
        logger.info(
            f"Historical version saved as {HISTORY_PATH / f'{Path(filename).stem}_{DATE}.txt'}"
        )

    def _normalize_exclude_paths(self, exclude_paths: List[str] | None) -> List[str]:
        if isinstance(exclude_paths, str):
            return [exclude_paths]
        return exclude_paths or []

    def _normalize_file_types(self, file_types: List[str] | None) -> List[str]:
        if isinstance(file_types, str):
            return file_types.split(",")
        return file_types or [".py", ".md", ".ipynb", ".js", ".html", ".css", ".json", ".yaml"]

    def _generate_filename(self, target_directory: Path, file_types: List[str]) -> str:
        relative_target = target_directory.relative_to(PROJECT_PATH)
        base_name = (
            f'{relative_target.as_posix().replace("/", "_")}_code'
            if target_directory != PROJECT_PATH
            else "all_project_code"
        )
        notebooks_suffix = "with_notebooks" if ".ipynb" in file_types else "no_notebooks"
        file_types_suffix = "_".join([ft[1:] for ft in file_types])
        return f"{base_name}_{notebooks_suffix}_no_empty_{file_types_suffix}.txt"

    def _get_notebooks_dirs(self, directory: Path) -> List[Path]:
        return [
            Path(root) / "notebooks" for root, dirs, _ in os.walk(directory) if "notebooks" in dirs
        ]

    def _load_gitignore_patterns(self, directory: Path) -> List[str]:
        patterns = []
        for gitignore in directory.rglob(".gitignore"):
            with gitignore.open() as f:
                patterns.extend(
                    [
                        str(gitignore.parent / line.strip())
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                )
        return patterns

    def _process_notebooks(
        self, notebooks_dirs: List[Path], ignore_patterns: List[str]
    ) -> Dict[str, str]:
        notebook_files = {}
        for notebooks_dir in notebooks_dirs:
            notebooks = self._convert_notebooks_to_python(
                notebooks_dir, PYTHON_NOTEBOOKS_PATH, ignore_patterns
            )
            notebook_files.update(
                {
                    str(Path(notebooks_dir).relative_to(PROJECT_PATH) / nb): py
                    for nb, py in notebooks.items()
                }
            )
        return notebook_files

    def _get_files(
        self,
        directory: Path,
        ignore_patterns: List[str],
        file_types: List[str],
        exclude_paths: List[str],
    ) -> List[Path]:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        files = []
        for file in directory.rglob("*"):
            if (
                file.suffix in file_types
                and not spec.match_file(str(file))
                and file.stat().st_size > 0
            ):
                if any(file.is_relative_to(directory / Path(ep)) for ep in exclude_paths):
                    logger.debug(f"Excluding file: {file}")
                else:
                    files.append(file.relative_to(directory))
        return files

    def _write_files_to_txt(
        self,
        file_paths: List[Path],
        output_file: Path,
        base_dir: Path,
        notebook_files: Dict[str, str],
    ) -> None:
        with output_file.open("w") as outfile:
            self._write_tree_structure(outfile, base_dir)
            self._write_file_contents(outfile, file_paths, base_dir)
            self._write_notebook_contents(outfile, notebook_files, base_dir)

    def _write_tree_structure(self, outfile, base_dir: Path) -> None:
        tree_output = subprocess.check_output(
            ["tree", "-I", "__pycache__|data|misc|venv", "--prune", str(base_dir)], text=True
        )
        outfile.write(f"Project Structure:\n```\n{tree_output}```\n\n")
        outfile.write("Note: Empty files are not included in the list.\n\n")

    def _write_file_contents(self, outfile, file_paths: List[Path], base_dir: Path) -> None:
        for file_path in file_paths:
            content = (base_dir / file_path).read_text()
            lang = (
                file_path.suffix[1:] if file_path.suffix in [".py", ".md", ".html"] else "plaintext"
            )
            outfile.write(f"{file_path}\n```{lang}\n{content}```\n\n")

    def _write_notebook_contents(
        self, outfile, notebook_files: Dict[str, str], base_dir: Path
    ) -> None:
        for notebook_path, py_file_path in notebook_files.items():
            code = Path(py_file_path).read_text()
            outfile.write(f"{notebook_path}\n```ipynb\n{code}\n```\n\n")

    def _copy_to_clipboard(self, file_path: Path) -> None:
        pyperclip.copy(file_path.read_text())

    def _save_historical_version(self, filename: str, output_file_path: Path) -> None:
        historical_file_path = HISTORY_PATH / f"{Path(filename).stem}_{DATE}.txt"
        historical_file_path.write_text(output_file_path.read_text())

    def _convert_notebooks_to_python(
        self, notebooks_dir: Path, output_dir: Path, ignore_patterns: List[str]
    ) -> Dict[str, str]:
        notebook_files = {}
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        for notebook in notebooks_dir.rglob("*.ipynb"):
            if not spec.match_file(str(notebook)):
                py_file_path = output_dir / f"{notebook.stem}.py"
                subprocess.run(
                    [
                        "jupyter",
                        "nbconvert",
                        "--to",
                        "script",
                        "--no-prompt",
                        str(notebook),
                        f"--output={py_file_path}",
                    ],
                    capture_output=True,
                )
                notebook_files[str(notebook.relative_to(notebooks_dir))] = str(py_file_path)
        return notebook_files
