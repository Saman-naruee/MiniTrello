from django.core.management.base import BaseCommand
import os
from bs4 import BeautifulSoup
import re

class Command(BaseCommand):
    help = 'Prepares HTML files for internationalization by adding {% load i18n %} and converting text to {% trans %} tags'

    def handle(self, *args, **options):
        # Get all HTML files recursively
        for root, dirs, files in os.walk('.'):
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

        # Check if {% load i18n %} already exists
        if '{% load i18n %}' not in content:
            content = '{% load i18n %}\n' + content

        # Parse HTML
        soup = BeautifulSoup(content, 'html.parser')

        # Find all text nodes in relevant tags
        text_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div', 'a', 'button', 'label']
        
        for tag in soup.find_all(text_tags):
            # Skip if tag is inside a script or style tag
            if tag.parent.name in ['script', 'style']:
                continue

            # Process direct text nodes
            for text in tag.find_all(text=True, recursive=False):
                if text.strip() and not self.is_template_tag(text):
                    wrapped_text = '{{% trans "{}" %}}'.format(text.strip())
                    text.replace_with(wrapped_text)

        # Convert back to string
        modified_content = str(soup)

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

    def is_template_tag(self, text):
        # Check if text is already a Django template tag
        return bool(re.match(r'{%.*?%}|{{.*?}}', str(text).strip()))
