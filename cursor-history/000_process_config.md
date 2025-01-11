# Cursor Composer Process Configuration

## Core Responsibilities

1. Test Management
   - Track all test cases in `todo.md`
   - Document each test case in `cursor-history/`
   - Ensure each test has clear acceptance criteria
   - Validate test results before marking complete

2. Documentation Flow
   ```mermaid
   graph TD
     A[Identify Issue] --> B[Create Test Doc]
     B --> C[Implement Test]
     C --> D[Document Results]
     D --> E[Update todo.md]
     E --> F[Git Commit]
     F --> G[Mark Resolved]
   ```

3. File Structure Maintenance
   ```
   project/
   ├── cursor-history/     # Test documentation
   │   ├── 000_process_config.md
   │   └── NNN_test_case.md
   ├── tests/              # Test implementations
   ├── src/                # Source code
   └── todo.md            # Master task list
   ```

## Operating Procedures

### For Each Test Case:
1. Pre-Implementation
   - Create test documentation file
   - Define acceptance criteria
   - Link documentation in todo.md
   - Set up test environment

2. During Implementation
   - Follow modular design principles
   - Add detailed logging
   - Document all changes
   - Run tests incrementally

3. Post-Implementation
   - Verify acceptance criteria
   - Update documentation
   - Commit changes
   - Update todo.md status

### Documentation Standards
1. Test Cases
   - Issue description
   - Implementation details
   - Current status
   - Next steps
   - Acceptance criteria

2. Code Changes
   - Purpose of change
   - Implementation details
   - Test results
   - Verification steps

3. Commit Messages
   - Reference test case ID
   - Brief description
   - List of changes
   - Test results

## Quality Gates

### Before Implementation:
- [ ] Test case documented
- [ ] Acceptance criteria defined
- [ ] Dependencies identified
- [ ] Test environment ready

### During Implementation:
- [ ] Following modular design
- [ ] Adding proper logging
- [ ] Documenting changes
- [ ] Running tests

### Before Marking Complete:
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Changes committed
- [ ] todo.md updated

## Error Handling

1. Test Failures
   - Document failure details
   - Update test case status
   - Create sub-issues if needed
   - Track in todo.md

2. Documentation Gaps
   - Flag missing information
   - Update relevant files
   - Maintain consistency
   - Track changes

## Configuration Updates

This configuration should be reviewed and updated:
- After completing each major feature
- When new requirements are added
- If process inefficiencies are identified
- When new test patterns emerge

## Current Configuration Version: 1.0.0
Last Updated: [Current Date]
Status: Active 