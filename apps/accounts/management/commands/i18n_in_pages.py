from django.core.management.base import BaseCommand
import os
from bs4 import BeautifulSoup
import re

class Command(BaseCommand):
    help = 'Prepares HTML files for internationalization by adding {% load i18n %} as second tag after extends'

    def should_skip_directory(self, dir_path):
        skip_dirs = ['env', 'venv', '.env', '.venv']
        return any(venv_dir in dir_path.split(os.sep) for venv_dir in skip_dirs)

    def handle(self, *args, **options):
        for root, dirs, files in os.walk('.'):
            if self.should_skip_directory(root):
                continue
                
            for file in files:
                if file.endswith('.html'):
                    file_path = os.path.join(root, file)
                    self.process_html_file(file_path)
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully processed {file_path}')
                    )

    def process_html_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Remove existing i18n load tag if present
        content = re.sub(r'{%\s*load\s+i18n\s*%}[\n\r]*', '', content)

        # Split content into lines
        lines = content.split('\n')
        new_lines = []
        extends_found = False
        i18n_added = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for extends tag
            if re.search(r'{%\s*extends.*?%}', line):
                new_lines.append(line)  # Add extends first
                new_lines.append('{% load i18n %}')  # Add i18n second
                extends_found = True
                i18n_added = True
                continue

            # Add other lines
            new_lines.append(line)

        # If no extends found, add both tags at the start
        if not extends_found:
            new_lines.insert(0, '{% load i18n %}')

        # Process HTML content
        content = '\n'.join(new_lines)
        soup = BeautifulSoup(content, 'html.parser')

        # Find all text nodes in relevant tags
        text_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div', 'a', 'button', 'label']
        
        for tag in soup.find_all(text_tags):
            if tag.parent.name in ['script', 'style']:
                continue

            for text in tag.find_all(text=True, recursive=False):
                if text.strip() and not self.is_template_tag(text):
                    wrapped_text = '{{% trans "{}" %}}'.format(text.strip())
                    text.replace_with(wrapped_text)

        # Convert back to string and ensure proper spacing
        modified_content = str(soup)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    def is_template_tag(self, text):
        return bool(re.match(r'{%.*?%}|{{.*?}}', str(text).strip()))
