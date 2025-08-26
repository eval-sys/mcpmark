# Notion

This guide walks you through preparing your Notion environment for MCPMark and authenticating the CLI tools.

## 1 · Set up Notion Environment

1. **Duplicate the MCPMark Source Pages**
   Copy the template database and pages into your workspace from the public template following this tutorial:
   [Duplicate MCPMark Source](https://painted-tennis-ebc.notion.site/MCPBench-Source-Hub-23181626b6d7805fb3a7d59c63033819).

2. **Set up the Source and Eval Hub for Environment Isolation**
   - Prepare **two separate Notion pages**:
     - **Source Hub**: Stores all the template databases/pages. Managed by `SOURCE_NOTION_API_KEY`.
     - **Eval Hub**: Only contains the duplicated templates for the current evaluation. Managed by `EVAL_NOTION_API_KEY`.
   - In Notion, create an **empty page** in your Eval Hub. The page name **must exactly match** the value you set for `EVAL_PARENT_PAGE_TITLE` in your environment variables (e.g., `MCPMark Eval Hub`).
   - In Notion's **Connections** settings:
     - Bind the integration corresponding to `EVAL_NOTION_API_KEY` to the Eval Hub parent page you just created.
     - Bind the integration corresponding to `SOURCE_NOTION_API_KEY` to your Source Hub (where the templates are stored).

3. **Create Notion Integrations & Grant Access**
   
   a. Visit [Notion Integrations](https://www.notion.so/profile/integrations) and create **two internal integrations** (one for Source Hub, one for Eval Hub).
   
   b. Copy the generated **Internal Integration Tokens** (these will be your `SOURCE_NOTION_API_KEY` and `EVAL_NOTION_API_KEY`).
   
   c. Share the **Source Hub** with the Source integration, and the **Eval Hub parent page** with the Eval integration (*Full Access*).

   ![Source Page](../../asset/notion/source_page.png)
   ![Create Integration](../../asset/notion/create_integration.png)
   ![API Access](../../asset/notion/api_access.png)
   ![Grant Access Source](../../asset/notion/grant_access_source.png)
   ![Grant Access Eval](../../asset/notion/grant_access_eval.png)

---

## 2 · Authenticate with Notion

```bash
# First, install Playwright and the browser binaries
playwright install
# Then, run the Notion login helper with your preferred browser
python -m src.mcp_services.notion.notion_login_helper --browser {firefox|chromium}
```

The verification script will tell you which browser is working properly. The pipeline defaults to using **chromium**. Our pipeline has been **fully tested on macOS and Linux**.

## 3. Running Notion Tasks

1. Configure environment variables: make sure the following service credentials are added in `.mcp_env`.
```env
## Notion
SOURCE_NOTION_API_KEY="your-source-notion-api-key"   # For Source Hub (templates)
EVAL_NOTION_API_KEY="your-eval-notion-api-key"       # For Eval Hub (active evaluation)
EVAL_PARENT_PAGE_TITLE="MCPMark Eval Hub"           # Must match the name of the empty page you created in Eval Hub
PLAYWRIGHT_BROWSER="chromium" # default to chromium, you can also choose firefox
PLAYWRIGHT_HEADLESS="True"
```

2. For single task or task group, run 
```bash
python -m pipeline --exp-name EXPNAME --mcp notion --tasks NOTIONTASK --models MODEL --k K
```
Here *EXPNAME* refers to customized experiment name, *NOTIONTASK* refers to the notion task or task group selected (see [Task Page](../datasets/task.md) for specific task information), *MODEL* refers to the selected model (see [Introduction Page](../introduction.md) for model supported), *K* refers to the time of independent experiments.
