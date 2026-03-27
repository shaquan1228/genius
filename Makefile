.PHONY: all build test lint fmt clean setup teardown

all: lint test build

# ── Build ────────────────────────────────────────────────────────────────────
build:
	cd dashboard && go build -o ../bin/dashboard-go .

# ── Test ─────────────────────────────────────────────────────────────────────
test: test-shell test-go

test-shell:
	bats test/

test-go:
	cd dashboard && go test ./...

# ── Lint ─────────────────────────────────────────────────────────────────────
lint: lint-shell lint-go

lint-shell:
	shellcheck bin/setup bin/teardown bin/link bin/worktree bin/worktree-agent bin/worktree-cleanup bin/tmux-init-session bin/dashboard

lint-go:
	cd dashboard && go vet ./...

# ── Format ───────────────────────────────────────────────────────────────────
fmt:
	cd dashboard && gofmt -w .

# ── Setup / Teardown ─────────────────────────────────────────────────────────
setup:
	bin/setup

teardown:
	bin/teardown --dry-run

# ── Clean ────────────────────────────────────────────────────────────────────
clean:
	rm -f bin/dashboard-go
