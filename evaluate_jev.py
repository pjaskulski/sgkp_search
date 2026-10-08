"""Evaluate Jev through OpenRouter on the labelled XLSX cases."""
from evaluate_tev1 import main


if __name__ == '__main__':
    raise SystemExit(main(backend='openrouter', default_model='typesafe/jev-1.13',
                          default_url='https://openrouter.ai/api/alpha/decisions'))
