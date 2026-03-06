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

export type SessionSummary = {
    id: string;
    name: string;
    project_id: string;
    created_at: string;
    updated_at?: string | null;
    message_count: number;
    asset_count: number;
    last_activity: string;
};

export type SessionMessage = {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
};

export type SessionAsset = {
    id: string;
    asset_type: string;
    drive_url?: string | null;
    drive_direct_url?: string | null;
    created_at: string;
};

export type SessionDetail = {
    id: string;
    name: string;
    project_id: string;
    created_at: string;
    updated_at?: string | null;
    messages: SessionMessage[];
    assets: SessionAsset[];
};
