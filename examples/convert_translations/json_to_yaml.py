from NekoGram.text_processors.yaml_processor import YAMLProcessor
import json
import os


if __name__ == '__main__':
    # Make sure `converted_translations` directory exists
    if not os.path.exists('converted_translations'):
        os.makedirs('converted_translations')

    # Convert all JSON files located in `translations` directory to YAML files and put them to `converted_translations`
    for file in os.listdir('translations'):
        if file.endswith('.json'):
            with open(f'translations/{file}', 'r', encoding='utf-8') as f:
                file = file.replace('.json', '.yml')
                YAMLProcessor.convert_data(json.load(f), f'converted_translations/{file}')
