# Mintlify Starter Kit

Use the starter kit to get your docs deployed and ready to customize.

Click the green **Use this template** button at the top of this repo to copy the Mintlify starter kit. The starter kit contains examples with

- Guide pages
- Navigation
- Customizations
- API reference pages
- Use of popular components

**[Follow the full quickstart guide](https://starter.mintlify.com/quickstart)**

## AI-assisted writing

Set up your AI coding tool to work with Mintlify:

```bash
npx skills add https://mintlify.com/docs
```

This command installs Mintlify's documentation skill for your configured AI tools like Claude Code, Cursor, Windsurf, and others. The skill includes component reference, writing standards, and workflow guidance.

See the [AI tools guides](/ai-tools) for tool-specific setup.

## Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mint) to preview your documentation changes locally. To install, use the following command:

```
npm i -g mint
```

Run the following command at the root of your documentation, where your `docs.json` is located:

```
mint dev
```

View your local preview at `http://localhost:3000`.

## Publishing changes

Install our GitHub app from your [dashboard](https://dashboard.mintlify.com/settings/organization/github-app) to propagate changes from your repo to your deployment. Changes are deployed to production automatically after pushing to the default branch.

## 龍蝦搬運工 (Lobster Porter)

The `lobster_porter` Python package is included in this repository. It provides batch file transport, organisation, and classification for any documentation workflow.

### Quick start

```python
from lobster_porter import Porter

# Move all files from ./inbox into ./organised, grouped by extension
porter = Porter(src="./inbox", dest="./organised")
results = porter.run()
print(f"Transported {sum(r.success for r in results)} files.")
```

### Using a custom strategy

```python
from lobster_porter import Porter
from lobster_porter.strategies import DateStrategy, CompositeStrategy, ExtensionStrategy

# Group by date first, then fall back to extension
porter = Porter(
    src="./inbox",
    dest="./organised",
    strategy=CompositeStrategy([DateStrategy(), ExtensionStrategy()]),
    copy=True,         # copy instead of move
    overwrite=False,   # skip files that already exist at destination
)
porter.run()
```

### Using plugins

```python
from lobster_porter import Porter
from lobster_porter.plugins.examples import LoggingPlugin, SummaryPlugin, FileCounterPlugin

counter = FileCounterPlugin()
porter = Porter(
    src="./inbox",
    dest="./organised",
    plugins=[LoggingPlugin(), SummaryPlugin(), counter],
)
porter.run()
print(counter.counts)  # {'md': 5, 'pdf': 3, ...}
```

### Package layout

```
lobster_porter/
├── __init__.py          # Public API + version
├── core.py              # Porter orchestrator class
├── strategies.py        # Built-in classification strategies
└── plugins/
    ├── __init__.py      # Plugin sub-package
    ├── base.py          # BasePlugin abstract class
    └── examples.py      # Ready-to-use example plugins
```

## Need help?

### Troubleshooting

- If your dev environment isn't running: Run `mint update` to ensure you have the most recent version of the CLI.
- If a page loads as a 404: Make sure you are running in a folder with a valid `docs.json`.

### Resources
- [Mintlify documentation](https://mintlify.com/docs)
