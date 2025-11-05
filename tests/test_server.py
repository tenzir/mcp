import pytest
from fastmcp.tools.tool import ToolResult

from mcp.types import TextContent
from tenzir_mcp.tools.documentation import docs_read, docs_search
from tenzir_mcp.tools.ocsf import (
    ocsf_get_class,
    ocsf_get_classes,
    ocsf_get_latest_version,
    ocsf_get_object,
    ocsf_get_versions,
)

# Access the underlying functions from the FunctionTool objects
docs_read = docs_read.fn
ocsf_get_classes = ocsf_get_classes.fn
ocsf_get_class = ocsf_get_class.fn
ocsf_get_object = ocsf_get_object.fn
docs_search = docs_search.fn
ocsf_get_versions = ocsf_get_versions.fn
ocsf_get_latest_version = ocsf_get_latest_version.fn


def docs_available():
    """Check if documentation files are available."""
    try:
        from tenzir_mcp.docs import TenzirDocs

        docs = TenzirDocs()
        # Try to access the docs root
        return docs.docs_root.exists()
    except Exception:
        return False


@pytest.mark.skipif(not docs_available(), reason="Documentation files not available")
class TestDocsTools:
    @pytest.mark.asyncio
    async def test_get_docs_markdown_function(self):
        """Test retrieving function documentation."""
        result = await docs_read("reference/functions/abs")
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert result.structured_content.get("path") == "reference/functions/abs"
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        text = result.content[0].text
        assert "abs" in text
        assert "absolute value" in text.lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_operator(self):
        """Test retrieving operator documentation."""
        result = await docs_read("reference/operators/read_json")
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert result.structured_content.get("path") == "reference/operators/read_json"
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        text = result.content[0].text
        assert "read_json" in text
        assert "JSON" in text

    @pytest.mark.asyncio
    async def test_get_docs_markdown_with_extension(self):
        """Test retrieving documentation with file extension."""
        result = await docs_read("reference/functions/abs.md")
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert result.structured_content.get("path") == "reference/functions/abs"
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert "abs" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_docs_markdown_nonexistent(self):
        """Test handling of nonexistent documentation."""
        result = await docs_read("nonexistent/path")
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"].lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_ocsf_function(self):
        """Test retrieving OCSF function documentation."""
        result = await docs_read("reference/functions/ocsf/category_name")
        assert isinstance(result, ToolResult)
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert "category_name" in result.content[0].text

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_file(self):
        """Test retrieving .mdoc documentation."""
        result = await docs_read("explanations/index")
        assert isinstance(result, ToolResult)
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        text = result.content[0].text
        assert "Explanations" in text
        assert "big-picture" in text

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_with_extension(self):
        """Test retrieving .mdoc documentation with extension."""
        result = await docs_read("explanations/index.mdoc")
        assert isinstance(result, ToolResult)
        assert isinstance(result.content, list)
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert "Explanations" in result.content[0].text

    # Note: docs_list_operators and docs_list_functions removed
    # Users should use docs_read("/reference/operators") or docs_read("/reference/functions") instead

    @pytest.mark.asyncio
    async def test_docs_search(self):
        """Search results include See Also metadata."""
        result = await docs_search(query="from", depth=1)
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert "results" in result.structured_content
        assert any(
            item["path"].endswith("reference/operators/from")
            for item in result.structured_content["results"]
        )
        for item in result.structured_content["results"]:
            assert "see_also" in item
        from_entry = next(
            item
            for item in result.structured_content["results"]
            if item["path"].endswith("reference/operators/from")
        )
        assert "related" in from_entry
        assert isinstance(from_entry["related"], list)
        assert from_entry["related"]

    @pytest.mark.asyncio
    async def test_docs_search_paths(self):
        """Paths parameter returns expanded related docs."""
        result = await docs_search(paths=["reference/operators/from"], depth=1, limit=1)
        assert isinstance(result, ToolResult)
        assert result.structured_content is not None
        assert result.structured_content["count"] == 1
        node = result.structured_content["results"][0]
        assert node["path"].endswith("reference/operators/from")
        assert "related" in node
        assert node["related"]


class TestOCSFTools:
    @pytest.mark.asyncio
    async def test_get_ocsf_versions(self):
        result = await ocsf_get_versions()
        assert isinstance(result, ToolResult)
        assert "versions" in result.structured_content
        versions = result.structured_content["versions"]
        assert isinstance(versions, list)
        assert len(versions) > 0
        for version in versions:
            assert isinstance(version, str)
            assert len(version) > 0
        assert versions == sorted(versions)

    @pytest.mark.asyncio
    async def test_get_newest_ocsf_version(self):
        result = await ocsf_get_latest_version()
        assert isinstance(result, ToolResult)
        version = result.structured_content["version"]
        assert isinstance(version, str)
        assert len(version) > 0
        assert "dev" not in version.lower()
        assert "alpha" not in version.lower()
        assert "beta" not in version.lower()
        assert "rc" not in version.lower()

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_valid_version(self):
        versions_result = await ocsf_get_versions()
        versions = versions_result.structured_content["versions"]
        version = versions[0]
        result = await ocsf_get_classes(version)
        assert isinstance(result, ToolResult)
        assert "classes" in result.structured_content
        classes = result.structured_content["classes"]
        assert isinstance(classes, dict)
        for key, value in classes.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_invalid_version(self):
        result = await ocsf_get_classes("invalid-version")
        assert isinstance(result, ToolResult)
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_valid_version_and_class(self):
        versions_result = await ocsf_get_versions()
        versions = versions_result.structured_content["versions"]
        version = versions[0]  # Use first available version
        result = await ocsf_get_class(version, "security_finding")
        assert isinstance(result, ToolResult)
        data = result.structured_content
        assert "error" not in data
        assert "id" in data
        assert "name" in data
        assert "data" in data
        assert data["name"] == "security_finding"

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_version(self):
        result = await ocsf_get_class("invalid-version", "security_finding")
        assert isinstance(result, ToolResult)
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_class(self):
        versions_result = await ocsf_get_versions()
        versions = versions_result.structured_content["versions"]
        version = versions[0]
        result = await ocsf_get_class(version, "nonexistent_class")
        assert isinstance(result, ToolResult)
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_valid_version_and_object(self):
        versions_result = await ocsf_get_versions()
        versions = versions_result.structured_content["versions"]
        version = versions[0]  # Use first available version
        result = await ocsf_get_object(version, "email")
        assert isinstance(result, ToolResult)
        data = result.structured_content
        assert "error" not in data
        assert "id" in data
        assert "name" in data
        assert "data" in data
        assert data["name"] == "email"

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_version(self):
        result = await ocsf_get_object("invalid-version", "email")
        assert isinstance(result, ToolResult)
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_object(self):
        versions_result = await ocsf_get_versions()
        versions = versions_result.structured_content["versions"]
        version = versions[0]
        result = await ocsf_get_object(version, "nonexistent_object")
        assert isinstance(result, ToolResult)
        assert "error" in result.structured_content
        assert "not found" in result.structured_content["error"]
