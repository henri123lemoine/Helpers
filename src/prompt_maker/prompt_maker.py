import fnmatch
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pathspec
import pyperclip

from src.utils.settings import (
    DATA_PATH,
    DATE,
    HISTORY_PATH,
    PROJECT_PATH,
    PYTHON_NOTEBOOKS_PATH,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptMaker:
    """Handles prompt context generation."""

    def get_prompt_context(
        self,
        target_directory: str = "Python/",
        exclude_paths: list[str] | None = None,
        file_types: list[str] | None = None,
        tree: bool = True,  # @TODO: fix for extremely large trees that are not pruned by the contents of exclude_paths/gitignore; must fix the tree command
    ) -> None:
        target_directory = Path(os.path.expanduser(target_directory)).resolve()
        logger.debug(f"Target directory: {target_directory}")

        exclude_paths = self._normalize_exclude_paths(exclude_paths)
        logger.debug(f"Exclude paths: {exclude_paths}")

        file_types = self._normalize_file_types(file_types)
        logger.debug(f"File types: {file_types}")

        filename = self._generate_filename(target_directory, file_types)
        logger.debug(f"Generated filename: {filename}")

        ignore_patterns = self._load_gitignore_patterns(target_directory)
        logger.debug(f"Ignore patterns: {ignore_patterns}")

        file_paths = self._get_files(target_directory, ignore_patterns, file_types, exclude_paths)
        logger.debug(f"File paths: {file_paths}")

        output_file_path = DATA_PATH / filename
        logger.debug(f"Output file path: {output_file_path}")

        self._write_files_to_txt(file_paths, output_file_path, target_directory, tree)
        self._copy_to_clipboard(output_file_path)
        self._save_historical_version(filename, output_file_path)

        logger.info(
            f"All specified files have been written to {output_file_path} and copied to the clipboard."
        )
        logger.info(
            f"Historical version saved as {HISTORY_PATH / f'{Path(filename).stem}_{DATE}.txt'}"
        )

    def _normalize_exclude_paths(self, exclude_paths: list[str] | None) -> list[str]:
        if isinstance(exclude_paths, str):
            paths = [path.strip() for path in exclude_paths.split(",")]
        else:
            paths = exclude_paths or []
        return paths

    def _normalize_file_types(self, file_types: list[str] | None) -> list[str]:
        if isinstance(file_types, str):
            return file_types.split(",")
        return file_types or [".py", ".md", ".ipynb", ".js", ".html", ".css", ".json", ".yaml"]

    def _generate_filename(self, target_directory: Path, file_types: list[str]) -> str:
        try:
            relative_target = target_directory.relative_to(PROJECT_PATH)
            base_name = f'{relative_target.as_posix().replace("/", "_")}_code'
        except ValueError:
            # If target_directory is not relative to PROJECT_PATH, use its name
            base_name = f"{target_directory.name}_code"

        notebooks_suffix = "with_notebooks" if ".ipynb" in file_types else "no_notebooks"
        file_types_suffix = "_".join([ft[1:] for ft in file_types])
        return f"{base_name}_{notebooks_suffix}_no_empty_{file_types_suffix}.txt"

    def _load_gitignore_patterns(self, directory: Path) -> list[str]:
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

    def _get_files(
        self,
        directory: Path,
        ignore_patterns: list[str],
        file_types: list[str],
        exclude_paths: list[str],
    ) -> list[Path]:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        files = []
        for file in directory.rglob("*"):
            if (
                file.is_file()
                and (file_types is None or file.suffix in file_types)
                and not spec.match_file(str(file))
                and file.stat().st_size > 0
            ):
                relative_path = file.relative_to(directory)
                if not self._should_exclude(relative_path, exclude_paths):
                    files.append(relative_path)
                else:
                    logger.debug(f"Excluding file: {relative_path}")
        return files

    def _should_exclude(self, path: Path, exclude_paths: list[str]) -> bool:
        str_path = str(path)
        for exclude_path in exclude_paths:
            if "*" in exclude_path:
                pattern = os.path.join("**", exclude_path)
                if fnmatch.fnmatch(str_path, pattern):
                    logger.debug(f"Excluding {str_path} (matched pattern {exclude_path})")
                    return True
            else:
                exclude_path = Path(exclude_path)
                if path == exclude_path or path.is_relative_to(exclude_path):
                    logger.debug(f"Excluding {str_path} (matched path {exclude_path})")
                    return True
        return False

    def _write_files_to_txt(
        self,
        file_paths: list[Path],
        output_file: Path,
        base_dir: Path,
        tree: bool = True,
    ) -> None:
        with output_file.open("w") as outfile:
            if tree:
                self._write_tree_structure(outfile, base_dir)
            self._write_file_contents(outfile, file_paths, base_dir)

    def _write_tree_structure(self, outfile, base_dir: Path) -> None:
        try:
            git_files = subprocess.check_output(
                ["git", "ls-files"], cwd=base_dir, text=True, stderr=subprocess.DEVNULL
            ).splitlines()

            tree_output = subprocess.check_output(
                ["tree", "--fromfile"],
                input="\n".join(git_files),
                cwd=base_dir,
                text=True,
                stderr=subprocess.DEVNULL,
            )

            outfile.write(f"Project Structure:\n```\n{tree_output}```\n\n")
            outfile.write("Note: This structure includes only Git-tracked files.\n\n")
        except subprocess.CalledProcessError:
            logger.warning("Failed to generate tree structure")
            outfile.write("Project Structure: Unable to generate tree structure.\n\n")

    def _write_file_contents(self, outfile, file_paths: list[Path], base_dir: Path) -> None:
        for file_path in file_paths:
            full_file_path = base_dir / file_path
            suffix = file_path.suffix
            lang = file_path.suffix.removeprefix(".")
            if suffix == ".ipynb":
                python_noteboook_path = PYTHON_NOTEBOOKS_PATH / f"{file_path.stem}"
                logger.debug(
                    f"Converting notebook {full_file_path} to Python file {python_noteboook_path}.py"
                )
                subprocess.run(
                    [
                        "jupyter",
                        "nbconvert",
                        "--to",
                        "script",
                        "--no-prompt",
                        str(full_file_path),
                        f"--output={python_noteboook_path}",
                    ],
                    capture_output=True,
                )
                with open(f"{python_noteboook_path}.py", "r") as f:
                    content = f.read()
            elif suffix == ".json":
                content = json.dumps(json.loads(content), indent=4)
            else:
                content = full_file_path.read_text()
            outfile.write(f"{file_path}\n```{lang}\n{content}```\n\n")

    def _copy_to_clipboard(self, file_path: Path) -> None:
        pyperclip.copy(file_path.read_text())

    def _save_historical_version(self, filename: str, output_file_path: Path) -> None:
        historical_file_path = HISTORY_PATH / f"{Path(filename).stem}_{DATE}.txt"
        historical_file_path.write_text(output_file_path.read_text())
