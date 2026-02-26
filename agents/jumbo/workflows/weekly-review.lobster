name: weekly-review
steps:
  - id: scan_archive
    command: cat archive/*.md 2>/dev/null || echo '{"posts":[]}'

  - id: scan_tasks
    command: cat task_board.md

  - id: compile_report
    command: echo '{"scan":"archive_and_tasks","status":"compiled"}'
    stdin: $scan_tasks.stdout

  - id: approve_report
    command: echo "Weekly review compiled. Approve to send summary to Telegram?"
    stdin: $compile_report.stdout
    approval: required

  - id: deliver
    command: echo '{"action":"send_report","approved":true}'
    condition: $approve_report.approved
