# MQTT RFC 준수 개선 사항

## 1. 인증 및 보안 추가
```python
def __init__(self, ..., username=None, password=None, ca_certs=None, tls_version=None):
    if username and password:
        self.client.username_pw_set(username, password)
    if ca_certs:
        self.client.tls_set(ca_certs=ca_certs, tls_version=tls_version)
```

## 2. Will Message 지원
```python
def set_will(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
    self.client.will_set(topic, payload, qos, retain)
```

## 3. 상세한 연결 코드 처리
```python
def _on_connect(self, client, userdata, flags, rc):
    if rc == 0:
        # 성공
    elif rc == 1:
        raise ProtocolError("Connection refused - incorrect protocol version")
    elif rc == 2:
        raise ProtocolError("Connection refused - invalid client identifier")
    elif rc == 3:
        raise ProtocolError("Connection refused - server unavailable")
    elif rc == 4:
        raise ProtocolAuthenticationError("Connection refused - bad username or password")
    elif rc == 5:
        raise ProtocolAuthenticationError("Connection refused - not authorised")
```

## 4. Retained Messages 지원
```python
def publish(self, topic: str, message: str, qos: int = 1, retain: bool = False) -> bool:
    result = self.client.publish(topic, message, qos, retain)
```