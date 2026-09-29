---
trigger: always_on
description: Strict workflow for context gathering and step-by-step execution on larger tasks.
---

# Step-by-Step Execution & Development Workflow

Whenever the user assigns a new task (e.g., building a feature, major refactoring, complex bug fixes), you MUST strictly adhere to the following step-by-step workflow.
**NOTE: This strict workflow does not apply to small, trivial fixes or minor bugs which can be resolved in a single step.**

1. **Step 1: Context Gathering & Planning**
   - **Do not write implementation code immediately.**
   - First, actively explore the monorepo to form a clear understanding of the relevant architecture, files, and current state.
   - Propose a breakdown of the task into simple, sequential steps.
   - Wait for the user to approve the plan before proceeding to the actual execution steps.

2. **Step N: Execution & Verification Loop**
   - Address **only one step at a time**.
   - Implement the code/changes required for the current step.
   - **Stop and wait.** Ask the user to test and verify the changes. 
   - Do NOT proceed to the next step until the user explicitly confirms they are satisfied with the current step.
   - If the user reports bugs, errors, or feedback, stay on the current step. Debug and fix the issues, then wait for verification again. Repeat this loop until the user is completely satisfied.

3. **Progression**
   - Once a step is verified and approved by the user, move on to the next step in the plan and repeat the Execution & Verification Loop.
   - Continue until all steps of the original task are complete.
