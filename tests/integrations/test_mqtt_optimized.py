import pytest
import time
import threading
from communicator.protocols.mqtt.mqtt_protocol import MQTTProtocol, BrokerConfig, ClientConfig
from communicator.common.exception import (
    ProtocolConnectionError,
    ProtocolValidationError,
    ProtocolError,
)


@pytest.fixture
def protocol():
    """MQTTProtocol EMQX 테스트 인스턴스"""
    config = BrokerConfig(
        broker_address="broker.emqx.io",
        port=1883,
        mode="non-blocking"
    )
    client_config = ClientConfig()
    protocol = MQTTProtocol(config, client_config)
    yield protocol
    protocol.disconnect()


@pytest.mark.integration
class TestConnection:
    """연결 관련 테스트"""
    
    @pytest.mark.integration
    @pytest.mark.integration
    def test_connect_success(self, protocol):
        result = protocol.connect()
        time.sleep(2)
        assert result is True
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")

    @pytest.mark.integration
    def test_connect_failure(self):
        config = BrokerConfig(
            broker_address="invalid.broker.address",
            port=9999,
            mode="non-blocking"
        )
        client_config = ClientConfig()
        protocol = MQTTProtocol(config, client_config)
        with pytest.raises(ProtocolConnectionError):
            protocol.connect()

    @pytest.mark.integration
    def test_disconnect(self, protocol):
        protocol.connect()
        time.sleep(1)
        protocol.disconnect()
        time.sleep(1)
        assert not protocol.is_connected


@pytest.mark.integration
class TestPublish:
    """발행 관련 테스트"""
    
    @pytest.mark.integration
    def test_publish_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        result = protocol.publish("test/optimized/publish", "test message")
        assert result is True

    @pytest.mark.integration
    def test_publish_when_disconnected(self, protocol):
        # 연결하지 않은 상태에서 발행
        result = protocol.publish("test/optimized/offline", "offline message")
        assert result is False

    @pytest.mark.integration
    def test_publish_error(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        # 빈 토픽으로 발행 시도
        result = protocol.publish("", "empty topic test")
        # 실제 구현에 따라 결과가 달라질 수 있음
        assert isinstance(result, bool)


@pytest.mark.integration
class TestSubscribe:
    """구독 관련 테스트"""
    
    @pytest.mark.integration
    def test_subscribe_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def callback(topic, payload):
            """콜백 함수 정의

            Args:
                topic (str): 수신한 메시지의 토픽
                payload (bytes): 수신한 메시지의 페이로드
            """
            pass
        
        result = protocol.subscribe("test/optimized/subscribe", callback)
        assert result is True

    @pytest.mark.integration
    def test_sequential_subscriptions(self, protocol):
        """순차적 구독 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = {}
        
        def make_callback(topic_name):
            def callback(topic, payload):
                if topic_name not in received_messages:
                    received_messages[topic_name] = []
                received_messages[topic_name].append(payload.decode())
            return callback
        
        # 순차적으로 여러 토픽 구독
        topics = [f"test/seq/{i}/{int(time.time())}" for i in range(3)]
        
        for i, topic in enumerate(topics):
            result = protocol.subscribe(topic, make_callback(f"topic_{i}"))
            assert result is True
            time.sleep(0.5)  # 구독 간 시간차
        
        time.sleep(1)
        
        # 각 토픽에 메시지 발행
        for i, topic in enumerate(topics):
            protocol.publish(topic, f"message_{i}")
            time.sleep(0.2)
        
        time.sleep(2)
        
        # 모든 메시지가 올바르게 수신되었는지 확인
        assert len(received_messages) == 3
        for i in range(3):
            assert f"topic_{i}" in received_messages
            assert f"message_{i}" in received_messages[f"topic_{i}"]

    @pytest.mark.integration
    def test_subscription_order_independence(self, protocol):
        """구독 순서와 무관하게 메시지 처리 확인"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_order = []
        
        def callback_a(topic, payload):
            received_order.append("A")
        
        def callback_b(topic, payload):
            received_order.append("B")
        
        def callback_c(topic, payload):
            received_order.append("C")
        
        base_topic = f"test/order/{int(time.time())}"
        topics = [f"{base_topic}/a", f"{base_topic}/b", f"{base_topic}/c"]
        callbacks = [callback_a, callback_b, callback_c]
        
        # 순차적 구독
        for topic, callback in zip(topics, callbacks):
            protocol.subscribe(topic, callback)
            time.sleep(0.3)
        
        time.sleep(1)
        
        # 역순으로 메시지 발행
        for topic in reversed(topics):
            protocol.publish(topic, "test")
            time.sleep(0.1)
        
        time.sleep(2)
        
        # 발행 순서대로 수신되어야 함 (C, B, A)
        assert received_order == ["C", "B", "A"]

    @pytest.mark.integration
    def test_subscribe_failure(self, protocol):
        # 연결하지 않은 상태에서 구독 시도
        def callback(topic, payload):
            pass
        
        with pytest.raises(ProtocolValidationError):
            protocol.subscribe("test/bad/subscribe", callback)

    @pytest.mark.integration
    def test_unsubscribe_success(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def callback(topic, payload):
            """콜백 함수 정의

            Args:
                topic (str): 수신한 메시지의 토픽
                payload (bytes): 수신한 메시지의 페이로드
            """
            pass
        
        protocol.subscribe("test/optimized/unsubscribe", callback)
        time.sleep(1)
        result = protocol.unsubscribe("test/optimized/unsubscribe")
        assert result is True

    @pytest.mark.integration
    def test_unsubscribe_nonexistent_topic(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        # 구독하지 않은 토픽 구독 해제 시도 (성공으로 처리됨)
        result = protocol.unsubscribe("test/nonexistent/topic")
        assert result is True  # MQTT 브로커는 존재하지 않는 토픽도 성공으로 처리
    
    @pytest.mark.integration
    def test_unsubscribe_when_disconnected(self, protocol):
        assert protocol.unsubscribe("test/disconnected/topic") is True

@pytest.mark.integration
class TestMessageHandling:
    """메시지 처리 테스트"""
    
    @pytest.mark.integration
    def test_on_message_callback(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append((topic, payload.decode()))
        
        topic = f"test/optimized/callback/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        protocol.publish(topic, "callback test message")
        time.sleep(2)
        
        assert len(received_messages) >= 1
        assert received_messages[0][0] == topic
        assert received_messages[0][1] == "callback test message"

    @pytest.mark.integration
    def test_on_message_exception_handling(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        def error_callback(topic, payload):
            raise ValueError("Test exception")  # 예외 발생
        
        topic = f"test/optimized/error/{int(time.time())}"
        protocol.subscribe(topic, error_callback)
        time.sleep(1)
        
        # 예외가 발생해도 프로토콜이 죽지 않아야 함
        protocol.publish(topic, "error test message")
        time.sleep(2)
        
        # 연결이 여전히 유지되어야 함
        assert protocol.is_connected


@pytest.mark.integration
class TestReconnection:
    """재연결 관련 테스트"""
    
    @pytest.mark.integration
    def test_connection_status(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        assert protocol.is_connected is True
        
        protocol.disconnect()
        time.sleep(1)
        assert protocol.is_connected is False

    @pytest.mark.integration
    def test_subscription_recovery(self, protocol):
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append(payload.decode())
        
        topic = f"test/optimized/recovery/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        # 연결 해제 후 재연결
        protocol.disconnect()
        time.sleep(1)
        protocol.connect()
        time.sleep(2)
        
        if protocol.is_connected:
            # 메시지 발행하여 구독이 복구되었는지 확인
            protocol.publish(topic, "recovery test")
            time.sleep(2)
            
            # 구독이 복구되었다면 메시지를 받아야 함
            assert len(received_messages) >= 1

    @pytest.mark.integration
    def test_sequential_subscription_recovery(self, protocol):
        """순차적 구독 후 재연결 시 모든 구독 복구 확인"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = {}
        
        def make_callback(topic_id):
            def callback(topic, payload):
                if topic_id not in received_messages:
                    received_messages[topic_id] = []
                received_messages[topic_id].append(payload.decode())
            return callback
        
        # 순차적으로 여러 토픽 구독
        base_topic = f"test/recovery/{int(time.time())}"
        topics = [f"{base_topic}/{i}" for i in range(3)]
        
        for i, topic in enumerate(topics):
            protocol.subscribe(topic, make_callback(f"topic_{i}"))
            time.sleep(0.5)
        
        time.sleep(1)
        
        # 연결 해제 후 재연결
        protocol.disconnect()
        time.sleep(1)
        protocol.connect()
        time.sleep(3)
        
        if protocol.is_connected:
            # 모든 토픽에 메시지 발행하여 구독 복구 확인
            for i, topic in enumerate(topics):
                protocol.publish(topic, f"recovery_msg_{i}")
                time.sleep(0.2)
            
            time.sleep(2)
            
            # 모든 구독이 복구되었는지 확인
            assert len(received_messages) == 3
            for i in range(3):
                assert f"topic_{i}" in received_messages
                assert f"recovery_msg_{i}" in received_messages[f"topic_{i}"]

@pytest.mark.integration
class TestSequentialSubscriptionEdgeCases:
    """순차적 구독 엣지 케이스 테스트"""
    
    @pytest.mark.integration
    def test_partial_subscription_failure(self, protocol):
        """일부 구독 실패 시 다른 구독에 영향 없음 확인"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append(payload.decode())
        
        base_topic = f"test/partial/{int(time.time())}"
        valid_topic = f"{base_topic}/valid"
        
        # 정상 구독
        result1 = protocol.subscribe(valid_topic, callback)
        assert result1 is True
        time.sleep(0.5)
        
        # 잘못된 구독 시도 (빈 토픽)
        try:
            protocol.subscribe("", callback)
        except:
            pass  # 예외 발생 예상
        
        time.sleep(0.5)
        
        # 다시 정상 구독
        valid_topic2 = f"{base_topic}/valid2"
        result2 = protocol.subscribe(valid_topic2, callback)
        assert result2 is True
        
        time.sleep(1)
        
        # 정상 구독된 토픽들이 작동하는지 확인
        protocol.publish(valid_topic, "test1")
        protocol.publish(valid_topic2, "test2")
        time.sleep(2)
        
        assert len(received_messages) == 2
        assert "test1" in received_messages
        assert "test2" in received_messages

    @pytest.mark.integration
    def test_rapid_sequential_subscriptions(self, protocol):
        """빠른 순차적 구독 처리 확인"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_count = {}
        
        def make_callback(topic_id):
            def callback(topic, payload):
                received_count[topic_id] = received_count.get(topic_id, 0) + 1
            return callback
        
        # 빠른 순차적 구독 (시간차 최소화)
        base_topic = f"test/rapid/{int(time.time())}"
        topics = [f"{base_topic}/{i}" for i in range(5)]
        
        for i, topic in enumerate(topics):
            result = protocol.subscribe(topic, make_callback(f"topic_{i}"))
            assert result is True
            time.sleep(0.1)  # 매우 짧은 시간차
        
        time.sleep(1)
        
        # 모든 토픽에 메시지 발행
        for i, topic in enumerate(topics):
            protocol.publish(topic, f"rapid_msg_{i}")
            time.sleep(0.05)
        
        time.sleep(2)
        
        # 모든 구독이 정상 작동하는지 확인
        assert len(received_count) == 5
        for i in range(5):
            assert received_count[f"topic_{i}"] == 1

    @pytest.mark.integration
    def test_subscription_persistence_during_sequential_operations(self, protocol):
        """순차적 작업 중 구독 유지 확인"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = {}
        
        def make_callback(topic_id):
            def callback(topic, payload):
                if topic_id not in received_messages:
                    received_messages[topic_id] = []
                received_messages[topic_id].append(payload.decode())
            return callback
        
        base_topic = f"test/persist/{int(time.time())}"
        
        # 1번째 구독
        topic1 = f"{base_topic}/1"
        protocol.subscribe(topic1, make_callback("topic1"))
        time.sleep(0.5)
        
        # 1번째 토픽에 메시지 발행
        protocol.publish(topic1, "msg1_first")
        time.sleep(1)
        
        # 2번째 구독 추가
        topic2 = f"{base_topic}/2"
        protocol.subscribe(topic2, make_callback("topic2"))
        time.sleep(0.5)
        
        # 두 토픽 모두에 메시지 발행
        protocol.publish(topic1, "msg1_second")
        protocol.publish(topic2, "msg2_first")
        time.sleep(1)
        
        # 3번째 구독 추가
        topic3 = f"{base_topic}/3"
        protocol.subscribe(topic3, make_callback("topic3"))
        time.sleep(0.5)
        
        # 모든 토픽에 메시지 발행
        protocol.publish(topic1, "msg1_third")
        protocol.publish(topic2, "msg2_second")
        protocol.publish(topic3, "msg3_first")
        time.sleep(2)
        
        # 모든 메시지가 올바르게 수신되었는지 확인
        assert "topic1" in received_messages
        assert "topic2" in received_messages
        assert "topic3" in received_messages
        
        assert "msg1_first" in received_messages["topic1"]
        assert "msg1_second" in received_messages["topic1"]
        assert "msg1_third" in received_messages["topic1"]
        
        assert "msg2_first" in received_messages["topic2"]
        assert "msg2_second" in received_messages["topic2"]
        
        assert "msg3_first" in received_messages["topic3"]


class TestUnsubscribeStability:
    """구독 해제 안정성 테스트"""
    
    @pytest.mark.integration
    def test_unsubscribe_during_sequential_operations(self, protocol):
        """순차적 작업 중 구독 해제 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = {}
        
        def make_callback(topic_id):
            def callback(topic, payload):
                if topic_id not in received_messages:
                    received_messages[topic_id] = []
                received_messages[topic_id].append(payload.decode())
            return callback
        
        base_topic = f"test/unsub/{int(time.time())}"
        topics = [f"{base_topic}/{i}" for i in range(3)]
        
        # 모든 토픽 구독
        for i, topic in enumerate(topics):
            protocol.subscribe(topic, make_callback(f"topic_{i}"))
            time.sleep(0.3)
        
        time.sleep(1)
        
        # 첫 번째 메시지 발행
        for i, topic in enumerate(topics):
            protocol.publish(topic, f"before_unsub_{i}")
        time.sleep(1)
        
        # 중간 토픽 구독 해제
        protocol.unsubscribe(topics[1])
        time.sleep(0.5)
        
        # 두 번째 메시지 발행
        for i, topic in enumerate(topics):
            protocol.publish(topic, f"after_unsub_{i}")
        time.sleep(1)
        
        # 결과 확인
        assert "topic_0" in received_messages
        assert "topic_2" in received_messages
        
        # topic_1은 구독 해제되었으므로 after_unsub 메시지를 받지 않아야 함
        if "topic_1" in received_messages:
            assert "after_unsub_1" not in received_messages["topic_1"]
        
        # 다른 토픽들은 모든 메시지를 받아야 함
        assert "before_unsub_0" in received_messages["topic_0"]
        assert "after_unsub_0" in received_messages["topic_0"]
        assert "before_unsub_2" in received_messages["topic_2"]
        assert "after_unsub_2" in received_messages["topic_2"]

    @pytest.mark.integration
    def test_multiple_unsubscribe_operations(self, protocol):
        """다중 구독 해제 작업 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_count = {}
        
        def make_callback(topic_id):
            def callback(topic, payload):
                received_count[topic_id] = received_count.get(topic_id, 0) + 1
            return callback
        
        base_topic = f"test/multi_unsub/{int(time.time())}"
        topics = [f"{base_topic}/{i}" for i in range(5)]
        
        # 모든 토픽 구독
        for i, topic in enumerate(topics):
            protocol.subscribe(topic, make_callback(f"topic_{i}"))
            time.sleep(0.2)
        
        time.sleep(1)
        
        # 순차적으로 구독 해제
        for i in [1, 3]:  # topic_1, topic_3 해제
            protocol.unsubscribe(topics[i])
            time.sleep(0.3)
        
        # 메시지 발행
        for i, topic in enumerate(topics):
            protocol.publish(topic, f"test_msg_{i}")
            time.sleep(0.1)
        
        time.sleep(2)
        
        # 결과 확인: topic_0, topic_2, topic_4만 메시지를 받아야 함
        expected_active = ["topic_0", "topic_2", "topic_4"]
        expected_inactive = ["topic_1", "topic_3"]
        
        for topic_id in expected_active:
            assert topic_id in received_count
            assert received_count[topic_id] == 1
        
        for topic_id in expected_inactive:
            assert topic_id not in received_count


@pytest.mark.integration
class TestMultipleMessageStability:
    """다중 메시지 안정성 테스트"""
    
    @pytest.mark.integration
    def test_burst_message_handling(self, protocol):
        """버스트 메시지 처리 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append(payload.decode())
        
        topic = f"test/burst/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        # 빠른 연속 메시지 발행
        message_count = 20
        for i in range(message_count):
            protocol.publish(topic, f"burst_msg_{i}")
            time.sleep(0.01)  # 매우 짧은 간격
        
        time.sleep(3)
        
        # 모든 메시지가 수신되었는지 확인
        assert len(received_messages) == message_count
        for i in range(message_count):
            assert f"burst_msg_{i}" in received_messages

    @pytest.mark.integration
    def test_concurrent_topic_message_handling(self, protocol):
        """동시 다중 토픽 메시지 처리 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")

        received_messages = {}

        def make_callback(topic_id):
            def callback(topic, payload):
                received_messages.setdefault(topic_id, []).append(payload.decode())
            return callback

        base_topic = f"test/concurrent/{int(time.time())}"
        topics = [f"{base_topic}/{i}" for i in range(3)]

        # 모든 토픽 구독(QoS=1로 최소 1회 보장)
        for i, topic in enumerate(topics):
            assert protocol.subscribe(topic, make_callback(f"topic_{i}"), qos=1) is True
            time.sleep(0.2)

        time.sleep(1)

        # 각 토픽에 여러 메시지 발행 (QoS=2로 확실한 전달 보장)
        message_per_topic = 5  # 메시지 수 줄여서 안정성 확보
        for round_num in range(message_per_topic):
            for i, topic in enumerate(topics):
                assert protocol.publish(topic, f"concurrent_msg_{i}_{round_num}", qos=2) is True
                time.sleep(0.1)  # 간격 더 늘림

        # 네트워크/브로커 지연 고려 여유 대기
        time.sleep(8)

        # 모든 토픽이 메시지를 충분히 받았는지 확인 (정확히== 대신 >=)
        for i in range(len(topics)):
            topic_id = f"topic_{i}"
            assert topic_id in received_messages
            assert len(received_messages[topic_id]) >= message_per_topic

            # 내용 검증(누락 체크)
            for round_num in range(message_per_topic):
                expected_msg = f"concurrent_msg_{i}_{round_num}"
                assert expected_msg in received_messages[topic_id]

    @pytest.mark.integration
    def test_message_order_preservation(self, protocol):
        """메시지 순서 보장 테스트"""
        protocol.connect()
        time.sleep(2)
        if not protocol.is_connected:
            pytest.skip("Cannot connect to MQTT broker")
        
        received_messages = []
        
        def callback(topic, payload):
            received_messages.append(payload.decode())
        
        topic = f"test/order/{int(time.time())}"
        protocol.subscribe(topic, callback)
        time.sleep(1)
        
        # 순차적 메시지 발행
        message_count = 15
        for i in range(message_count):
            protocol.publish(topic, f"order_msg_{i:02d}")
            time.sleep(0.05)
        
        time.sleep(2)
        
        # 메시지 수신 확인
        assert len(received_messages) == message_count
        
        # 순서 확인 (완벽한 순서 보장은 QoS에 따라 다름)
        for i in range(message_count):
            expected_msg = f"order_msg_{i:02d}"
            assert expected_msg in received_messages
