from NekoGram.text_processors import JSONProcessor
import yaml  # pip install pyyaml
import os


if __name__ == '__main__':
    # Make sure `converted_translations` directory exists
    if not os.path.exists('converted_translations'):
        os.makedirs('converted_translations')

    # Convert all JSON files located in `translations` directory to YAML files and put them to `converted_translations`
    for file in os.listdir('translations'):
        if file.endswith('.yml'):
            with open(f'translations/{file}', 'r', encoding='utf-8') as f:
                file = file.replace('.yml', '.json')
                JSONProcessor.convert_data(yaml.safe_load(f), f'converted_translations/{file}')
