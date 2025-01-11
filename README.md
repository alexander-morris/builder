# Build Agent CLI

A command-line interface for managing and executing build requests in a sandboxed environment.

## Setup Instructions

1. **Prerequisites**
   - Python 3.8 or higher
   - pip (Python package installer)
   - virtualenv (recommended)

2. **Installation**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd <repository-name>

   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Running the CLI**
   ```bash
   python3 agent_cli.py
   ```

## Usage

The CLI provides several commands for managing build requests:

1. **Create a new build request**
   ```bash
   (agent) build Create a React todo app with local storage
   ```

2. **Check status of current request**
   ```bash
   (agent) status
   ```

3. **Process next step in current request**
   ```bash
   (agent) next
   ```

4. **List all active requests**
   ```bash
   (agent) list
   ```

5. **Exit the CLI**
   ```bash
   (agent) quit
   ```
   Or press Ctrl+D

## Features

- Intelligent todo generation based on project type
- Progress tracking for build requests
- State persistence between sessions
- Mock sandbox environment for testing
- Support for different project types:
  - React applications
  - API services
  - General projects

## Project Structure

```
.
├── src/
│   ├── api/
│   │   └── claude_client.py
│   ├── sandbox/
│   │   └── environment.py
│   ├── agent_interface.py
│   └── cli.py
├── agent_cli.py
├── requirements.txt
└── README.md
```

## Development Status

Currently running in mock mode for demonstration purposes. Future updates will include:
- Docker sandbox integration
- Real-time build execution
- Project template generation
- Automated testing and deployment

## Command Reference

| Command | Description |
|---------|-------------|
| `build <description>` | Create a new build request |
| `status` | Show current build request status |
| `next` | Process next step in current request |
| `list` | Show all active build requests |
| `quit` | Exit the CLI |
| `help` | Show available commands |

## Example Session

```bash
$ python3 agent_cli.py
Welcome to the Build Agent CLI. Type help or ? to list commands.

(agent) build Create a React todo app
Created new build request:
Description: Create a React todo app

Generated todos:
  1. Initialize new React project with create-react-app
  2. Set up project structure (components, styles, etc.)
  ...

(agent) status
Current build request:
Description: Create a React todo app
Status: pending
Progress: 0/8 steps

(agent) next
Completed: Initialize new React project with create-react-app

(agent) quit
Goodbye!
``` 