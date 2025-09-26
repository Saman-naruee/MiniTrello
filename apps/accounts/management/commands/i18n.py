import os
import re
import glob
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.template import Template, Context
from django.utils import translation
import argparse


class Command(BaseCommand):
    help = 'Internationalizes HTML templates by adding i18n tags and preparing language files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without modifying files',
        )
        parser.add_argument(
            '--add-language',
            type=str,
            help='Add a new language code (e.g., fa, ar, fr)',
        )
        parser.add_argument(
            '--templates-only',
            action='store_true',
            help='Only process template files, skip language setup',
        )
        parser.add_argument(
            '--language-only',
            action='store_true',
            help='Only set up language files, skip template processing',
        )
        parser.add_argument(
            '--template-dirs',
            nargs='*',
            default=['templates', 'apps/*/templates'],
            help='Specify template directories to process',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        add_language = options['add_language']
        templates_only = options['templates_only']
        language_only = options['language_only']
        template_dirs = options['template_dirs']

        # Set up new language if specified
        if add_language:
            self.setup_new_language(add_language, dry_run)
            return

        # Process templates if not language-only
        if not language_only:
            self.process_templates(template_dirs, dry_run)

        # Set up language files if not templates-only
        if not templates_only:
            self.setup_language_files(dry_run)

        if not add_language:
            self.stdout.write(
                self.style.SUCCESS('HTML template internationalization completed successfully!')
            )

    def setup_new_language(self, language_code, dry_run):
        """Set up a new language by creating locale directory and files"""
        locale_dir = os.path.join(settings.BASE_DIR, 'locale')

        if not os.path.exists(locale_dir):
            if not dry_run:
                os.makedirs(locale_dir)
            self.stdout.write(f"Created locale directory: {locale_dir}")

        lang_dir = os.path.join(locale_dir, language_code, 'LC_MESSAGES')
        if not dry_run:
            os.makedirs(lang_dir, exist_ok=True)

        # Create main translation files
        files_to_create = [
            os.path.join(lang_dir, 'django.po'),
            os.path.join(lang_dir, 'djangojs.po'),
        ]

        template_content = '''# Translation file for {language_code}
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: {date}\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: {language_code}\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
'''

        date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for file_path in files_to_create:
            if not os.path.exists(file_path):
                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        content = template_content.format(
                            language_code=language_code,
                            date=date_str
                        )
                        f.write(content)

                self.stdout.write(
                    self.style.SUCCESS(f"Created: {file_path}")
                )
            else:
                self.stdout.write(f"File already exists: {file_path}")

        # Update Django settings to include the new language
        self.update_settings_for_language(language_code, dry_run)

    def update_settings_for_language(self, language_code, dry_run):
        """Update Django settings to include the new language"""
        settings_path = self.find_settings_file()

        if not settings_path:
            self.stdout.write(
                self.style.WARNING("Could not find settings file to update")
            )
            return

        with open(settings_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for LANGUAGES setting
        languages_pattern = r"LANGUAGES\s*=\s*\[(.*?)\]"
        match = re.search(languages_pattern, content, re.DOTALL)

        if match:
            current_languages = match.group(1)
            # Check if language is already there
            if f"'{language_code}'" not in current_languages:
                new_languages = current_languages.rstrip() + f"\n    ('{language_code}', '{self.get_language_name(language_code)}'),"
                new_content = content.replace(match.group(0), f"LANGUAGES = [{new_languages}\n]")

                if not dry_run:
                    with open(settings_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                self.stdout.write(
                    self.style.SUCCESS(f"Added language '{language_code}' to settings")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Language '{language_code}' already exists in settings")
                )

        # Also add to USE_I18N if not present
        if 'USE_I18N = True' not in content:
            new_content = content.replace(
                'USE_I18N = False',
                'USE_I18N = True'
            ).replace(
                '# USE_I18N = True',
                'USE_I18N = True'
            )

            if not dry_run and new_content != content:
                with open(settings_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.stdout.write(
                    self.style.SUCCESS("Enabled USE_I18N in settings")
                )

    def find_settings_file(self):
        """Find the main Django settings file"""
        possible_paths = [
            'MiniTrello/settings.py',
            'MiniTrello/config/base.py',
            'config/base.py',
        ]

        for path in possible_paths:
            full_path = os.path.join(settings.BASE_DIR, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def get_language_name(self, code):
        """Get human-readable language name from code"""
        language_names = {
            'fa': 'Persian',
            'ar': 'Arabic',
            'fr': 'French',
            'de': 'German',
            'es': 'Spanish',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'hi': 'Hindi',
        }
        return language_names.get(code, code.upper())

    def process_templates(self, template_dirs, dry_run):
        """Process all HTML templates for internationalization"""
        processed_files = 0
        modified_files = 0

        # Find all HTML files
        html_files = []
        for dir_pattern in template_dirs:
            if '*' in dir_pattern:
                # Handle glob patterns
                for pattern in glob.glob(os.path.join(settings.BASE_DIR, dir_pattern)):
                    if os.path.isdir(pattern):
                        html_files.extend(self.find_html_files(pattern))
            else:
                full_path = os.path.join(settings.BASE_DIR, dir_pattern)
                if os.path.exists(full_path):
                    html_files.extend(self.find_html_files(full_path))

        self.stdout.write(f"Found {len(html_files)} HTML files to process")

        for html_file in html_files:
            processed_files += 1
            relative_path = os.path.relpath(html_file, settings.BASE_DIR)

            try:
                # Read the file
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content

                # Process the content
                modified_content = self.process_template_content(content, html_file)

                if modified_content != original_content:
                    modified_files += 1
                    if not dry_run:
                        with open(html_file, 'w', encoding='utf-8') as f:
                            f.write(modified_content)
                    self.stdout.write(
                        self.style.SUCCESS(f"Modified: {relative_path}")
                    )
                else:
                    self.stdout.write(f"No changes: {relative_path}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing {relative_path}: {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Processed {processed_files} files, modified {modified_files}")
        )

    def find_html_files(self, directory):
        """Recursively find all HTML files in a directory"""
        html_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        return html_files

    def process_template_content(self, content, filepath):
        """Process a single template's content for i18n"""
        lines = content.split('\n')
        processed_lines = []

        # Check if {% load i18n %} is already present
        has_i18n_load = any('{% load i18n %}' in line for line in lines[:10])

        # Handle different template structures
        if lines and '{% extends' in lines[0]:
            # Template extends another template
            if not has_i18n_load:
                # Insert i18n load after extends
                i = 0
                while i < len(lines):
                    processed_lines.append(lines[i])
                    if '{% extends' in lines[i] and i + 1 < len(lines) and '{% load' not in lines[i + 1]:
                        # Insert i18n load after extends
                        if i + 1 < len(lines):
                            processed_lines.append('{% load i18n %}')
                    i += 1
            else:
                processed_lines = lines.copy()
        else:
            # Standalone template or template without extends
            if not has_i18n_load:
                # Add i18n load at the beginning
                processed_lines.append('{% load i18n %}')
                processed_lines.extend(lines)
            else:
                processed_lines = lines.copy()

        # Now process the entire content to wrap translatable strings
        content_str = '\n'.join(processed_lines)
        processed_content = self.wrap_translatable_strings(content_str)

        return processed_content

    def wrap_translatable_strings(self, content):
        """Wrap HTML content with trans tags where appropriate"""
        # Pattern to match HTML tags with text content
        # This will match common text-containing tags and wrap their content
        patterns = [
            # Basic text tags
            (r'(<p[^>]*>)\s*(.+?)\s*(</p>)', r'\1{% trans "\2" %}\3'),
            (r'(<h1[^>]*>)\s*(.+?)\s*(</h1>)', r'\1{% trans "\2" %}\3'),
            (r'(<h2[^>]*>)\s*(.+?)\s*(</h2>)', r'\1{% trans "\2" %}\3'),
            (r'(<h3[^>]*>)\s*(.+?)\s*(</h3>)', r'\1{% trans "\2" %}\3'),
            (r'(<h4[^>]*>)\s*(.+?)\s*(</h4>)', r'\1{% trans "\2" %}\3'),
            (r'(<h5[^>]*>)\s*(.+?)\s*(</h5>)', r'\1{% trans "\2" %}\3'),
            (r'(<h6[^>]*>)\s*(.+?)\s*(</h6>)', r'\1{% trans "\2" %}\3'),

            # Button content
            (r'(<button[^>]*>)\s*(.+?)\s*(</button>)', r'\1{% trans "\2" %}\3'),

            # Label content
            (r'(<label[^>]*>)\s*(.+?)\s*(</label>)', r'\1{% trans "\2" %}\3'),

            # Span content (if not class-based)
            (r'(<span[^>]*(?<!class)[^>]*>)\s*(.+?)\s*(</span>)', r'\1{% trans "\2" %}\3'),

            # List item content
            (r'(<li[^>]*>)\s*(.+?)\s*(</li>)', r'\1{% trans "\2" %}\3'),

            # Title attributes in various tags
            (r'(title=")([^"]+)(")', r'\1{% trans "\2" %}\3'),
            (r"(title=')([^']+)(')", r"\1{% trans \"\2\" %}\3"),

            # Alt attributes in images
            (r'(alt=")([^"]+)(")', r'\1{% trans "\2" %}\3'),
            (r"(alt=')([^']+)(')", r"\1{% trans \"\2\" %}\3"),

            # Placeholder attributes
            (r'(placeholder=")([^"]+)(")', r'\1{% trans "\2" %}\3'),
            (r"(placeholder=')([^']+)(')", r"\1{% trans \"\2\" %}\3"),
        ]

        # Modal and alert content
        modal_pattern = r'(<div[^>]*(?:class[^>]*(?:modal|alert)[^>]*|id[^>]*modal[^>]*|role[^>]*dialog[^>]*).*?>)\s*(.+?)\s*(</div>)'
        patterns.append((modal_pattern, r'\1{% trans "\2" %}\3'))

        original_content = content
        changes_made = False

        # Apply patterns - process multiple times to handle nested content
        for _ in range(3):
            for pattern, replacement in patterns:
                if pattern == modal_pattern:
                    # Handle modals more carefully
                    def modal_replacement(match):
                        opening_tag = match.group(1)
                        content = match.group(2)
                        closing_tag = match.group(3)

                        # Only wrap if it doesn't already have trans tags
                        if '{% trans' not in content:
                            return f'{opening_tag}{{% trans "{content}" %}}{closing_tag}'
                        return match.group(0)

                    content = re.sub(pattern, modal_replacement, content, flags=re.DOTALL)
                else:
                    # Regular pattern replacement
                    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                    if new_content != content:
                        changes_made = True
                        content = new_content

        # Special handling for titles and headings that might have Django template variables
        content = self.handle_template_variables(content)

        # Only process if we actually made changes
        if changes_made or '{% load i18n %}' in content:
            return content

        return original_content

    def handle_template_variables(self, content):
        """Handle Django template variables in translatable strings"""
        # Look for patterns like {% trans "Hello {{ user.name }}" %}
        # And fix them to proper format
        trans_pattern = r'{%\s*trans\s*"([^"]*(?:\{\{\s*[^}]+\s*\}\}[^"]*)*)"\s*%}'

        def fix_trans_tags(match):
            text = match.group(1)
            # If the text contains template variables, use blocktrans
            if '{{' in text and '}}' in text:
                # Split the text and template variables
                parts = re.split(r'(\{\{\s*[^}]+\s*\}\})', text)
                result = '{% blocktrans %}'

                for part in parts:
                    if part.strip().startswith('{{') and part.strip().endswith('}}'):
                        # This is a template variable
                        var_name = part.strip()[2:-2].strip()
                        result += f'{{{var_name}}}'
                    elif part.strip():
                        # This is text
                        result += part.strip()

                result += '{% endblocktrans %}'
                return result
            else:
                # Regular trans is fine
                return match.group(0)

        return re.sub(trans_pattern, fix_trans_tags, content)

    def setup_language_files(self, dry_run):
        """Set up language configuration files"""
        # Make sure Django settings has proper i18n configuration
        settings_path = self.find_settings_file()

        if settings_path:
            # Create a basic locale middleware configuration if not present
            with open(settings_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add locale middleware if not present
            middleware_pattern = r"MIDDLEWARE\s*=\s*\[(.*?)\]"
            middleware_match = re.search(middleware_pattern, content, re.DOTALL)

            if middleware_match and 'LocaleMiddleware' not in middleware_match.group(1):
                current_middleware = middleware_match.group(1)
                new_middleware = current_middleware.rstrip() + "\n    'django.middleware.locale.LocaleMiddleware',"

                new_content = content.replace(middleware_match.group(0), f"MIDDLEWARE = [{new_middleware}\n]")
                new_content = new_content.replace('django.middleware.common.CommonMiddleware',
                                                "django.middleware.locale.LocaleMiddleware',\n    'django.middleware.common.CommonMiddleware")

                if not dry_run and new_content != content:
                    with open(settings_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.stdout.write(
                        self.style.SUCCESS("Added LocaleMiddleware to settings")
                    )

        # Create a basic .po template file
        self.create_pot_file(dry_run)

    def create_pot_file(self, dry_run):
        """Create a messages.pot file for translations"""
        locale_dir = os.path.join(settings.BASE_DIR, 'locale')

        if not os.path.exists(locale_dir):
            if not dry_run:
                os.makedirs(locale_dir)
            self.stdout.write(f"Created locale directory: {locale_dir}")

        pot_file = os.path.join(locale_dir, 'messages.pot')

        content = '''# Translation template file
# Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: MiniTrello 1.0\\n"
"Report-Msgid-Bugs-To: \\n"
"POT-Creation-Date: {date}\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"Language: \\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"

# Common UI strings
msgid "Create Board"
msgstr ""

msgid "My Boards"
msgstr ""

msgid "No boards yet"
msgstr ""

msgid "Create your first board to get started!"
msgstr ""

msgid "Delete Board"
msgstr ""

msgid "Are you sure you want to delete this board?"
msgstr ""

msgid "This action cannot be undone."
msgstr ""

msgid "Cancel"
msgstr ""

msgid "Delete"
msgstr ""

msgid "Edit"
msgstr ""

msgid "View"
msgstr ""

msgid "Save"
msgstr ""

msgid "Submit"
msgstr ""

msgid "Close"
msgstr ""

# Form labels and placeholders
msgid "Title"
msgstr ""

msgid "Description"
msgstr ""

msgid "Color"
msgstr ""

msgid "Due Date"
msgstr ""

msgid "Priority"
msgstr ""

# Status messages
msgid "Board created successfully"
msgstr ""

msgid "Board updated successfully"
msgstr ""

msgid "Board deleted successfully"
msgstr ""
'''.format(date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        if not os.path.exists(pot_file):
            if not dry_run:
                with open(pot_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            self.stdout.write(
                self.style.SUCCESS(f"Created translation template: {pot_file}")
            )
        else:
            self.stdout.write(f"Template file already exists: {pot_file}")
