# GitHub Action CI/CD Bot

The Github Action CI/CD allows you to automate creating PR environments, checking for required approvers, and doing data gapless deployments to production.

## Getting Started
1. Make sure SQLMesh is added to your project's dependencies.
2. Create a new file in `.github/workflows/sqlmesh.yml` with the following contents:
```yaml
name: SQLMesh Bot
run-name: 🚀SQLMesh Bot 🚀
on:
  pull_request:
    types:
    - synchronize
    - opened
    - closed
  pull_request_review:
    types:
    - edited
    - submitted
    - dismissed
jobs:
  sqlmesh:
    name: SQLMesh
    runs-on: ubuntu-latest
    permissions:
      # Required to access code in PR
      contents: write
      # Required to post comments
      issues: write
      # Required to update check runs
      checks: write
      # Required to merge
      pull-requests: write
    steps:
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Checkout PR branch
        uses: actions/checkout@v3
      - name: Install SQLMesh + Dependencies
        run: pip install -r requirements.txt
        shell: bash
      - name: Run CI/CD Bot
        run: |
          sqlmesh_cicd -p ${{ github.workspace }} github --token ${{ secrets.GITHUB_TOKEN }} run-all
```
3. (Optional) If you want to designate users as required approvers, update your SQLMesh config file to represent this. YAML Example:
```yaml
users:
  - username: <A username to use within SQLMesh to represent the user>
    github_username: <Github username>
    roles:
      - required_approver
```
4. :tada: You're done! SQLMesh will now automatically create PR environments, check for required approvers (if configured), and do data gapless deployments to production.

## Environment Summaries

### Example Full Workflow
This workflow involves configuring a SQLMesh connection to Databricks and configuring access to GCP to talk to Cloud Composer (Airflow)
```yaml
name: SQLMesh Bot
run-name: 🚀SQLMesh Bot 🚀
on:
  pull_request:
    types:
    - synchronize
    - opened
    - closed
  pull_request_review:
    types:
    - edited
    - submitted
    - dismissed
jobs:
  sqlmesh:
    name: SQLMesh
    runs-on: ubuntu-latest
    permissions:
      contents: write
      # Required to post comments
      issues: write
      # Required to update check runs
      checks: write
      # Required to merge
      pull-requests: write
    env:
      SQLMESH__CONNECTIONS__DATABRICKS__TYPE: "databricks"
      SQLMESH__CONNECTIONS__DATABRICKS__SERVER_HOSTNAME: "XXXXXXXXXXXXXXX"
      SQLMESH__CONNECTIONS__DATABRICKS__HTTP_PATH: "XXXXXXXXXXXX"
      SQLMESH__CONNECTIONS__DATABRICKS__ACCESS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
      SQLMESH__DEFAULT_CONNECTION: "databricks"
    steps:
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Checkout PR branch
        uses: actions/checkout@v3
      - name: Install Dependencies
        run: pip install -r requirements.txt
        shell: bash
      - id: auth
        name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: '${{ secrets.GOOGLE_CREDENTIALS }}'
      - name: Run CI/CD Bot
        run: |
          sqlmesh_cicd -p ${{ github.workspace }} --token ${{ secrets.GITHUB_TOKEN }} run-all
```

<table>
    <tr>
        <th colspan="3">PR Environment Summary</th>
    </tr>
    <tr>
        <th>Model</th>
        <th>Change Type</th>
        <th>Dates Loaded</th>
    </tr>
    <tr>
        <td>db.item_d</td>
        <td>Breaking</td>
        <td>(2022-06-01 - 2023-05-01)</td>
    </tr>
</table>
| Model | Change Type | Dates Loaded |
| --- | --- | --- |
| db.item_d | Breaking | (2022-06-01 - 2023-05-01) |
| db.order_item_f | Indirect breaking | (2022-06-01 - 2023-05-01) |
| db.order_f | Indirect breaking | (2022-06-01 - 2023-05-01) |

PR Environment Summary
Model: db.item_d - Breaking
Dates Loaded: (2022-06-01 - 2023-05-01)
Model: db.order_item_f - Indirect breaking
Dates Loaded: (2022-06-01 - 2023-05-01)
Model: db.order_f - Indirect breaking
Dates Loaded: (2022-06-01 - 2023-05-01)