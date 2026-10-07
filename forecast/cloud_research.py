"""Compatibility entry point for the Development LightGBM collector."""


def main():
    from forecast.candidate_cloud import main as collect

    collect()


if __name__ == "__main__":
    import json

    try:
        main()
    except Exception as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
