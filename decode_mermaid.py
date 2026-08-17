import base64
import zlib
import json

encoded = "eNqNVH9vm0gQ_SorqpxaCVN-2MbmTneKDSROYpvW0UlXbFUrGNurYEDL0ti18t1vFgKxXUUq_8DsvveYeTuzRyXKYlAcZcNpviWP7pIvU4LP1RUxNDJJ81KQP8jXrBQs3TSb1x_DesdnCZCvEAH7AfHqE-l0_iajUBJjSAVbH8jjIYdXAVg1_FEFHB8nRa1ASeD6_7w02817jDDyHxQV2g3HWfoDuJBYEtANrouMTHbyq1V2K6wXmlq9QwIOnZxnERQFFrA6k55lNVountSN3HECNEU8Zu5C8QTPJ8V7FckPRyylnP2U1Uk4RzlWvNXoV7Cb0AUBkfTQZ3uyQClynW6SN9xNhbsNLY3cQslZIVhEHugBDUMkTQ4Fq8s7yRCx7iGlO0QGiylZPDMRbU9SvK00J0f5b75jKZCF4GUkSk4T8i1LobV6In2YlolgnUTiAspp3QpS4S68Rts2KXlE-4BTrKPTyYsd6a_OBBZMloSH_Ew-YxU0ltZJgfv3BOwLgZzyApA8ZXuIq9Ot-A_v8a1LS7oa8fYQYZtmKZr9L3C2ZhGVYYO6qySnYQsFkh9EI6wx2S_fRfY9poK26d3XpCZ8OA-b97RanoXeXlRJPsJeHjl27JrhJER4AFHGT_p0VhHmxxPEX8TWr34dAqytp5F5KXDeimZxfjoZQYgAP6Ebss44CbJCdIK249HTRQ5JEm0helqd8V_b_8vHsFZvmwRPoCrgM7lbzGerTw0rqPEXzi_EIYE2syihReHCmhSCcuGlMVmzJHE-eGPP9w21EDx7AueDZXftrv8adp5ZLLaOme___EXmdXYbFcs3fbdVMbzBwOv9hkoMEStkZ9Qyvu9bnt7K-KPBWNd_QwY4R4cbDW_kea2G17OG1jupnOmQa_VLa875L8hIdVVP9dUb9Va9U-_VB3WqzhoLLrBjdaLO28IuNoM61WpVUfFyZ7Hi4OmCquzwRqAyVI6SsVTEFnawVBz8jGFN8S5YKsv0BWk5Tb9l2a5h8qzcbBVnTZMCozLHOQGXyeviDQJpDHyclalQnKHZrTQU56jsFcfUe5rd1_uGbhrWoGf3TFU5KI4x1HSz2zWMwdDSe0O796IqP6u_GpqJXWIZ_X7XHvbNvm2-_A_aQQ-b"

try:
    # Handle URL-safe base64 padding
    padded = encoded + '=' * (4 - len(encoded) % 4)
    decoded_bytes = base64.urlsafe_b64decode(padded)
    decompressed = zlib.decompress(decoded_bytes)
    
    # The result is typically a JSON string for mermaid live editor
    data = json.loads(decompressed.decode('utf-8'))
    print(data.get('code', decompressed.decode('utf-8')))
except Exception as e:
    print("Error:", e)
