export type Project = {
    id: string;
    name: string;
};

export type GenerationJob = {
    id: string;
    project_id: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
};

export type CostEntry = {
    id: string;
    amount_usd: number;
    service: string;
    created_at: string;
};
