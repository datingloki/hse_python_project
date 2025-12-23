from typing import Dict


class EmailMessage:
    def __init__(self, message_data: Dict):
        self.id = message_data['id']
        self.headers = {h['name']: h['value'] for h in message_data['payload']['headers']}
        self.from_ = self.headers.get('From', 'Unknown')
        self.subject = self.headers.get('Subject', 'No Subject')
        self.snippet = message_data.get('snippet', '')