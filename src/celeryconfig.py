from kombu import Exchange, Queue

# Define the Dead Letter Exchange
dead_letter_exchange = Exchange('dead_letter_exchange', type='direct')

# Define the Dead Letter Queue
dead_letter_queue = Queue(
    'dead_letter_queue',
    dead_letter_exchange,
    routing_key='dead_letter'
)

# Define the main tasks queue with dead letter configuration
tasks_exchange = Exchange('tasks', type='direct')
tasks_queue = Queue(
    'tasks',
    tasks_exchange,
    routing_key='tasks',
    queue_arguments={
        'x-dead-letter-exchange': 'dead_letter_exchange',
        'x-dead-letter-routing-key': 'dead_letter'
    }
)

task_queues = (tasks_queue, dead_letter_queue)
task_default_queue = 'tasks'
task_default_exchange = 'tasks'
task_default_routing_key = 'tasks'
task_acks_late = True
task_reject_on_worker_lost = True
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 100

# Recommended Redis settings for production
broker_transport_options = {
    'visibility_timeout': 86400,  # 24 hours in seconds
    'retry_on_timeout': True,
    'socket_connect_timeout': 30,
    'socket_keepalive': True,
}

result_backend_transport_options = {
    'retry_on_timeout': True,
    'socket_connect_timeout': 30,
    'socket_keepalive': True,
}
