"""Evaluate basal-1.5-4.5B-GGUF via basal-serve on the same cases as tev1."""
from evaluate_tev1 import main


if __name__ == '__main__':
    raise SystemExit(main(backend='basal', default_model='basal-1.5-4.5B-GGUF',
                          default_url='http://localhost:8000'))
