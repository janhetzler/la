# Known issues

## Researcher tool calls

- **Symptom**: Crash with `EISDIR: illegal operation on a directory, read`
- **Cause**: Granite tiny-h calls `read_text_file` on a path that's actually a directory
- **Workaround**: Reinforce `SYSTEM_PROMPT` to remind Granite to call `list_directory` first
- **Future fix**: Use LangChain's `middleware` system to wrap MCP tools with try/except
  (current version doesn't expose `tool_node_kwargs` on `create_agent`)

## Open WebUI follow-ups

- **Symptom**: Phantom requests `{"follow_ups": [...]}` polluting agent logs
- **Cause**: Open WebUI auto-generates follow-up suggestions
- **Workaround**: Filter in `supervisor.invoke_supervisor` (already in place)
- **Better fix**: Disable Follow Up Generation in Open WebUI Settings → Interface
