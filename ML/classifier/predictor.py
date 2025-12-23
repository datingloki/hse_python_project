from ML.classifier.preprocessor import clean_email_text
import joblib
import pickle


class EmailClassifier:
    def __init__(self, model_dir='email_classifier_latest'):
        self.model = joblib.load(f'{model_dir}/model.pkl')
        with open(f'{model_dir}/vectorizer.pkl', 'rb') as f:
            self.vectorizer = pickle.load(f)
        with open(f'{model_dir}/label_encoder.pkl', 'rb') as f:
            self.label_encoder = pickle.load(f)

    def predict(self, email_text):
        clean_text = clean_email_text(email_text)

        features = self.vectorizer.transform([clean_text])

        prediction = self.model.predict(features)[0]
        probabilities = self.model.predict_proba(features)[0]

        category = self.label_encoder.inverse_transform([prediction])[0]

        prob_dict = {}
        for i, cat in enumerate(self.label_encoder.classes_):
            prob_dict[cat] = float(probabilities[i])

        return {
            'category': category,
            'confidence': float(probabilities[prediction]),
            'probabilities': prob_dict,
            'clean_text': clean_text[:100] + "..." if len(clean_text) > 100 else clean_text
        }

    def batch_predict(self, email_texts):
        """Предсказание для списка писем"""
        return [self.predict(text) for text in email_texts]