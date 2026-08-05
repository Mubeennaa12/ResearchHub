"""
Crawls GitHub repositories and extracts file layouts, dependencies, and code structures (AST).
"""

import os
import re
import ast
import shutil
import tempfile
import hashlib
import subprocess
from ingestion.base import BaseIngestor, NormalizedDocument, IngestionError


class GitHubIngestor(BaseIngestor):
    source_type = "github"

    def can_handle(self, source: str) -> bool:
        return "github.com" in source.lower()

    def _parse_repo_info(self, url: str) -> tuple[str, str]:
        """Extracts owner and repo name from URL."""
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if not match:
            raise ValueError(f"Could not parse owner/repo from URL: {url}")
        owner = match.group(1)
        repo = match.group(2).replace(".git", "")
        return owner, repo

    def _parse_python_ast(self, code_text: str) -> dict:
        """Parses python code using built-in AST to extract classes, functions, and imports."""
        try:
            root = ast.parse(code_text)
            classes = []
            functions = []
            imports = []
            for node in ast.walk(root):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            return {"classes": classes, "functions": functions, "imports": imports}
        except Exception:
            # Fallback in case of syntax errors or non-compiling code
            return {"classes": [], "functions": [], "imports": []}

    def _parse_js_ts(self, code_text: str) -> dict:
        """Regular expression fallback to extract classes, functions, and imports for JS/TS."""
        classes = re.findall(r"\bclass\s+([A-Za-z0-9_]+)", code_text)
        functions = re.findall(r"\bfunction\s+([A-Za-z0-9_]+)", code_text)
        arrow_funcs = re.findall(r"\b(?:const|let|var)\s+([A-Za-z0-9_]+)\s*=\s*(?:\([^\)]*\)|[A-Za-z0-9_]+)\s*=>", code_text)
        functions.extend(arrow_funcs)
        imports = re.findall(r"\bfrom\s+['\"]([^'\"]+)['\"]", code_text)
        return {
            "classes": list(set(classes)),
            "functions": list(set(functions)),
            "imports": list(set(imports))
        }

    def _is_binary(self, filepath: str) -> bool:
        """Heuristic to check if a file is binary."""
        try:
            with open(filepath, "tr") as f:
                f.read(1024)
                return False
        except UnicodeDecodeError:
            return True

    def ingest(self, source: str) -> NormalizedDocument:
        try:
            owner, repo = self._parse_repo_info(source)
        except Exception as e:
            raise IngestionError(f"GitHub Ingestion URL error: {e}")

        temp_dir = tempfile.mkdtemp(prefix="agy_git_")
        try:
            # Run git clone --depth 1 in command line
            subprocess.run(
                ["git", "clone", "--depth", "1", source, temp_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise IngestionError(f"Failed to clone repository: {source}. Ensure Git CLI is installed. Error: {e}")

        try:
            sections = []
            folder_structure = []
            ignored_folders = {".git", "node_modules", "venv", ".venv", "target", "build", "dist", "__pycache__"}
            ignored_files = {"package-lock.json", "yarn.lock", "poetry.lock", "cargo.lock", "go.sum"}
            
            for root_dir, dirs, files in os.walk(temp_dir):
                # Prune ignored folders
                dirs[:] = [d for d in dirs if d not in ignored_folders]

                for file in files:
                    if file in ignored_files:
                        continue
                    
                    full_path = os.path.join(root_dir, file)
                    rel_path = os.path.relpath(full_path, temp_dir)
                    folder_structure.append(rel_path)

                    if self._is_binary(full_path):
                        continue

                    # Determine language and extract structure
                    _, ext = os.path.splitext(file)
                    ext = ext.lower()

                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except Exception:
                        continue

                    ast_data = {"classes": [], "functions": [], "imports": []}
                    lang = "prose"

                    if ext == ".py":
                        lang = "python"
                        ast_data = self._parse_python_ast(content)
                    elif ext in [".js", ".jsx", ".ts", ".tsx"]:
                        lang = "javascript"
                        ast_data = self._call_js_ts_regex(content) if hasattr(self, "_call_js_ts_regex") else self._parse_js_ts(content)
                    elif ext in [".html", ".css", ".json", ".md", ".txt"]:
                        lang = "prose"

                    sections.append({
                        "type": "code",
                        "path": rel_path,
                        "language": lang,
                        "text": content,
                        "ast": ast_data
                    })

            # Format repository report as default full text
            readme_path = os.path.join(temp_dir, "README.md")
            readme_content = ""
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                        readme_content = f.read()
                except Exception:
                    pass

            full_text = f"Repository: {owner}/{repo}\n\nReadme:\n{readme_content}\n\nFolder structure:\n" + "\n".join(folder_structure)
            source_id = hashlib.md5(source.encode("utf-8")).hexdigest()

            return NormalizedDocument(
                source_id=source_id,
                source_type=self.source_type,
                title=f"{owner}/{repo}",
                text=full_text,
                url=source,
                metadata={
                    "owner": owner,
                    "repo": repo,
                    "folder_structure": folder_structure
                },
                sections=sections
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
