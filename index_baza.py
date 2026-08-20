import sys
from pathlib import Path
from memory import TranslationMemory, format_translation_memory_for_prompt

if __name__ == "__main__":
    base_dir = Path(r"c:\Users\Piotrek\Desktop\translator\baza napisów")
    tm = TranslationMemory()
    count = tm.index_database_directory(base_dir)
    print(f"\n[Gotowe]: Zaindeksowano {count} unikalnych par dialogowych.")

    test_queries = [
        "What are you doing?",
        "I'm home!",
        "Are you okay?",
        "What a pain...",
        "I see."
    ]
    matches = tm.find_relevant_examples(test_queries, max_examples=5)
    print("\nTest wyszukiwania dla typowych zwrotów:")
    print(format_translation_memory_for_prompt(matches))
