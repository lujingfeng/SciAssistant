# ================ AGENT TOOL SETS ================
# Define what tools each agent type should have access to

PLANNER_AGENT_TOOLS = [
  "download_files",
  "document_qa",

  "file_read",
  "file_write",
  "str_replace_based_edit_tool",

  "list_workspace",
  "file_find_by_name",
]


INFORMATION_SEEKER_TOOLS = [
  "batch_web_search",
  "url_crawler",
  "document_extract",
  "document_qa",
  "download_files",
  "file_read",
  "file_write",
  "str_replace_based_edit_tool",
  "list_workspace",
  "file_find_by_name",
]

WRITER_AGENT_TOOLS = [
  "file_read",
  "list_workspace",
  "file_find_by_name",

  "search_result_classifier",
  "section_writer",
  "concat_section_files",
]