# OODA Loop

The OODA loop is a decision-making framework that reduces cognitive load by making thinking explicit and iterative.

## What is OODA?

**Observe → Orient → Decide → Act**

Originally developed for fighter pilots, OODA is a continuous cycle for making decisions under uncertainty.

## Why OODA?

- **Reduces cognitive load** - Breaks complex decisions into small, explicit steps
- **Prevents analysis paralysis** - Forces action after observation
- **Makes thinking visible** - Easy to review and improve decision quality
- **Iterative by design** - Small reversible actions over big risky bets

## The Loop

### Observe

State the latest facts, signals, and constraints.

**Ask:**

- What changed since my last action?
- What new information do I have?
- What are the current constraints?

**Example:**

- "Test is failing on line 42"
- "User requested feature X"
- "Deadline is Friday"

### Orient

Name the governing pattern, risks, and tradeoffs for this step.

**Ask:**

- What pattern applies here? (TDD, boundary transformation, etc.)
- What are the risks if I proceed?
- What am I trading off?

**Example:**

- "This is a boundary validation problem"
- "Risk: Could break existing API contract"
- "Tradeoff: Speed vs. thoroughness"

### Decide

Choose the next smallest reversible action.

**Ask:**

- What's the smallest thing I can do to learn more?
- Is this action reversible?
- Does this move me toward my goal?

**Example:**

- "Write a failing test for the edge case"
- "Add validation at the boundary layer"
- "Refactor this one method first"

### Act

Execute, validate, and capture what changed.

**Ask:**

- Did my action produce the expected result?
- What did I learn?
- What's the new state?

**Example:**

- "Test now fails with clear error message"
- "Learned that input can be null"
- "Ready to implement validation logic"

## When to Apply OODA

### Always

- Non-trivial decisions (more than one viable option)
- Debugging complex issues
- Designing new features
- Reviewing code or architecture

### Not Necessary

- Trivial decisions (obvious next step)
- Routine tasks (following established pattern)
- Simple bug fixes (clear cause and solution)

## OODA in Practice

### Code Example

```
Observe: User registration fails when email is empty
Orient: This is input validation at the boundary
Decide: Add validation before calling domain logic
Act: Implement validation, test passes
→ Observe: Now need to handle duplicate emails...
```

### Session Example

```
Observe: User asked to "improve dev experience"
Orient: This is broad - need to clarify scope
Decide: Ask 3 clarifying questions about goals
Act: User responds with specific pain points
→ Observe: User wants tmux + iTerm2 integration...
```

## OODA and Cognitive Load

The loop reduces cognitive load by:

1. **Externalizing thought** - Write down observations instead of holding them in memory
2. **Forcing small steps** - Prevents overwhelm from trying to solve everything at once
3. **Making progress visible** - Each loop iteration produces observable change
4. **Enabling course correction** - Small actions are easy to undo or adjust

## Anti-Patterns

### Loop Too Big

**Bad:** Observe entire codebase, orient to all patterns, decide on complete refactor, act on 50 files

**Good:** Observe one failing test, orient to one pattern, decide on one change, act on one file

### Skipping Orient

**Bad:** Observe problem → immediately decide solution

**Good:** Observe problem → orient to risks/tradeoffs → decide solution

### No Iteration

**Bad:** Run loop once, assume done

**Good:** Run loop continuously until goal achieved

## Integration with Workflow

OODA is the micro-loop that runs **inside** each workflow step:

- **Clarify** - OODA to understand the request
- **Plan** - OODA to break down the work
- **Execute** - OODA for each implementation step
- **Verify** - OODA to validate results

See `docs/dev/WORKFLOW.md` for the complete development process.

## Summary

**OODA is how I think.**

Every non-trivial decision runs through the loop:

1. What do I see? (Observe)
2. What does it mean? (Orient)
3. What should I do? (Decide)
4. What happened? (Act)

Then repeat.

Small loops. Fast iterations. Low cognitive load.

For the broader operating framework, see `docs/dreams/FIELD-GENERAL.md`.
