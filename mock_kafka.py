
import json
import os
import time

class MockKafkaProducer:
    def __init__(self, bootstrap_servers=None, value_serializer=None):
        print("[MockKafka] Initialized Mock Producer (local file based)")
        self.topic_file = "kafka_mock_queue.txt"
        
    def send(self, topic, value):
        # Append to a local file acting as the queue
        with open(self.topic_file, "a") as f:
            f.write(json.dumps({'topic': topic, 'value': value, 'timestamp': time.time()}) + "\n")
        # print(f"[MockKafka] Sent to {topic}: {value}")
        
    def flush(self):
        pass
        
    def close(self):
        pass

class MockKafkaConsumer:
    def __init__(self, topic, bootstrap_servers=None, value_deserializer=None, **kwargs):
        print(f"[MockKafka] Initialized Mock Consumer for topic: {topic}")
        self.topic = topic
        self.topic_file = "kafka_mock_queue.txt"
        self.offset = 0
        
        # Create file if not exists
        if not os.path.exists(self.topic_file):
            with open(self.topic_file, "w") as f: pass
            
    def __iter__(self):
        while True:
            # Read new lines from file
            with open(self.topic_file, "r") as f:
                lines = f.readlines()
            
            if len(lines) > self.offset:
                for line in lines[self.offset:]:
                    if line.strip():
                        data = json.loads(line)
                        if data['topic'] == self.topic:
                            # Create a dummy message object
                            yield type('obj', (object,), {'value': data['value']})
                self.offset = len(lines)
            
            time.sleep(1) # Poll interval
