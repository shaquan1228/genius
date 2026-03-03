## Generic Pattern Examples (Pseudocode)

### Public Facade First

```text
# good
writeResult = Domain.command(input)
readResult = Domain.query(filters)

# avoid
result = InternalModule.HiddenImplementation.new(input).run()
```

### Single Orchestration Owner

```text
function completeWorkflow(input):
  validatedInput = validate(input)
  commandResult = Domain.command(validatedInput)
  publish(Event.WorkflowCompleted(commandResult.id))
  return commandResult
```

### Thin Subscriber

```text
on Event.PaymentChanged(data):
  planId = data.planId
  enqueue(Job.SyncOutstandingTasks, { planId: planId })
```

### Boundary Transformation

```text
function getBillingHistory(userId):
  rawRecords = ExternalBillingAPI.fetch(userId)
  normalized = BillingHistoryTransformer.normalize(rawRecords)
  return normalized
```

### Explicit Failure Policy

```text
try:
  process(event)
catch RetryableError:
  retryLater(event)
catch TerminalError:
  recordFailure(event)
catch IgnorableError:
  logAndDrop(event)
```

### Sprawl Smell vs Cohesion

```text
# smell
# controller mutates state
# subscriber mutates same state differently
# model callback mutates state again

# better
# one orchestrator owns state transitions
# other layers only call orchestrator
```

