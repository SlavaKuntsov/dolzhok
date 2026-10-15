"""Bot entrypoint (long polling). Full wiring lands in P1."""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("P0 skeleton: telegram wiring lands in P1 (SPEC-001)")


if __name__ == "__main__":
    main()
