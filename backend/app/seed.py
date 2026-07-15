"""Compatibility entry point for the retired automatic seed."""


def main() -> None:
    raise SystemExit(
        "Automatic demo seed is disabled. "
        "Use `python -m scripts.import_demo_showcase --dry-run` and then an explicit `--apply`."
    )


if __name__ == "__main__":
    main()
