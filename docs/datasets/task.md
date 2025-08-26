# Task

The tasks in MCPMark follows two major principles
- The tasks are based on realistic digital environments that are also used by human programmers.
- The task outcome can be robustly verified in python scripts.

Therefore, each MCPMark task consists of three files
- `meta.json`
- `description.md`
- `verify.py`

Here, `metadata.json` includes the meta information of the task, `description.md` describes the purpose and setting of the task, as well as the instruction to complete the task. `verify.py` checks whether the task is completed successfully.

For example, you can ask the model agent to create a file with specific name and write specific content to the file, which belongs to the cateogry of operating the file context. The structure looks like

```
tasks 
│
└───filesystem
   │
   └───file_context
      │
      └───create_file_write
         │   meta.json 
         │   description.md
         │   verify.py
```

Note that all tasks are placed under `tasks/`. `filesystem` refers to the environment for the MCP service.

`meta.json` includes the meta information about the task, including the following key
- task_id: the id of the task.
- task_name: full name of the task.
- description: task description.
- cateogry_id: the id of task category.
- cateogry_name: the full name of task categeory.
- author: the author of the task.
- difficulty: the task difficulty level.
- created_at: the timestamp of task creation.
- tags: a list of tags that describe the task.
- mcp: a list of MCP services it belongs to.
- metadata: other meta information.

Here `cateogry_name` describes the shared feature or the environment across different tasks (e.g. the github repository or notion page the task is built on). In this running example, `category_name` refers to `file_context`.

`description.md` could include the following information

- Task name
    - Create and Write File.
- Task description
    - Use the filesystem MCP tools to create a new file and write content to it.
- Task Objectives
    - Create a new file named `hello_world.txt` in the test directory.
    - Write the following content to the file:   ```   Hello, World```
    - Verify the file was created successfully
-  Verification Criteria
    - File `hello_world.txt` exists in the test directory
    - File contains the expected content structure
    - File includes "Hello, World!" on the first line
- Tips
    - Use the `write_file` tool to create and write content to the file
    - The test directory path will be provided in the task context

The entire content of `description.md` will be read by the model agent for completing the task. 

Accordingly, the `verify.py` contains the following functionalities
- Check whether the target directory exists. ![Check Target Directory](../../asset/task_sample/task_sample_verify_get_test_dir.png)
- Check whether the target directory contains the file with target file name. ![Check Target File Existence](../../asset/task_sample/task_sample_verify_file_existence.png)
- Check whether the target file contains the desired content `EXPECTED_PATTERNS = ["Hello Wolrd"]`. ![Check Content in Target File](../../asset/task_sample/task_sample_verify_check_content.png)
- If the outcome passes **all the above verification functionalities**, the task would be marked as successfully completed.