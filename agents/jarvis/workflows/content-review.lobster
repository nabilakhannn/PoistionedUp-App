name: content-review
args:
  task_id:
    required: true
  content_type:
    default: "carousel"
steps:
  - id: read_draft
    command: cat drafts/${task_id}-*.md

  - id: quality_check
    command: echo '{"task_id":"${task_id}","type":"${content_type}","status":"quality_check"}'
    stdin: $read_draft.stdout

  - id: approve_content
    command: echo "Content review complete. Ready for human approval."
    stdin: $quality_check.stdout
    approval: required

  - id: move_to_ready
    command: echo '{"action":"approve","task_id":"${task_id}","approved":true}'
    condition: $approve_content.approved
