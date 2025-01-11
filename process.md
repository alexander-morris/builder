# Development Process and Workflow

## Core Principles

1. **Continuous Execution**
   - Run code continuously during development
   - Test changes immediately after implementation
   - Verify functionality in real-time
   - Use automated tests whenever possible

2. **Log Monitoring**
   - Watch logs actively for errors and issues
   - Stop at first error encountered
   - Analyze error context before proceeding
   - Use LogWatcher to automate error detection

3. **Single Focus**
   - Work on one problem at a time
   - Complete current task before moving to next
   - Track progress in todo.md
   - Document completion criteria

4. **Progress Tracking**
   - Maintain todo.md as single source of truth
   - Update task status regularly
   - Include:
     - Priority number
     - Task description
     - Current status
     - Acceptance criteria
     - Next steps

5. **Version Control**
   - Commit after each successful problem resolution
   - Use semantic commit messages
   - Include task reference in commits
   - Keep changes focused and atomic

## Workflow Steps

1. **Task Selection**
   - Check todo.md for highest priority task
   - Verify task is well-defined
   - Ensure acceptance criteria are clear

2. **Implementation**
   - Write/modify code
   - Run tests continuously
   - Monitor logs for errors
   - Fix issues immediately

3. **Verification**
   - Run full test suite
   - Check log output
   - Verify against acceptance criteria
   - Document any edge cases

4. **Documentation**
   - Update todo.md with completion
   - Add any new tasks discovered
   - Document solutions and learnings

5. **Version Control**
   - Stage relevant files
   - Write semantic commit message
   - Include task reference
   - Push changes

## Error Handling

1. **When Error Detected**
   - Stop execution immediately
   - Capture error context
   - Analyze root cause
   - Document in todo.md if new issue

2. **Resolution Process**
   - Focus solely on current error
   - Implement fix
   - Verify fix with tests
   - Update documentation

## Continuous Improvement

1. **Process Refinement**
   - Review workflow effectiveness
   - Identify bottlenecks
   - Update process documentation
   - Implement improvements

2. **Tool Enhancement**
   - Maintain LogWatcher
   - Update test suites
   - Improve automation
   - Add new tools as needed 