# test_gemini.py
from google import genai

# YANGI API kalit
API_KEY = 'AIzaSyD9eBi7n8Tr20mgCzaNCKNWaFjT8kQn9aU'


def test_gemini():
    try:
        client = genai.Client(api_key=API_KEY)

        # Test so'rov
        print("Test so'rov yuborilmoqda...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Salom! 2+2 nechchi?'
        )
        print("\nJavob:")
        print(response.text)
        print("\n✅ API ishlayapti!")

    except Exception as e:
        print(f"\n❌ Xatolik: {type(e).__name__}")
        print(f"Xabar: {e}")


if __name__ == '__main__':
    test_gemini()