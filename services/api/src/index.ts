import Fastify from 'fastify';

const app = Fastify({ logger: true });

app.get('/health', async () => ({ status: 'ok', service: 'remi-api' }));

const port = Number(process.env.PORT ?? 3000);
await app.listen({ host: '0.0.0.0', port });
