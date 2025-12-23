from typing import Dict


class EmailMessage:
    def __init__(self, message_data: Dict):
        self.id = message_data['id']
        self.headers = {h['name']: h['value'] for h in message_data['payload']['headers']}
        self.from_ = self.headers.get('From', 'Unknown')
        self.subject = self.headers.get('Subject', 'No Subject')
        self.snippet = message_data.get('snippet', '')
        self.body = self._get_body(message_data)

    def _get_body(self, message_data):
        if 'parts' in message_data['payload']:
            parts = message_data['payload']['parts']
            for part in parts:
                if part.get('mimeType') == 'text/plain' and 'data' in part['body']:
                    import base64
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'data' in message_data['payload']['body']:
            import base64
            return base64.urlsafe_b64decode(message_data['payload']['body']['data']).decode('utf-8')
        return ''