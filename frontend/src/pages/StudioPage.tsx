import { ImageGenerator } from '../components/studio/ImageGenerator';
import { VideoGenerator } from '../components/studio/VideoGenerator';
import { Gallery } from '../components/studio/Gallery';
import { BatchProcessor } from '../components/studio/BatchProcessor';

export function StudioPage() {
    return (
        <div className="flex flex-col h-full p-6 space-y-6 overflow-y-auto">
            <div className="pb-4 border-b border-zinc-100">
                <h2 className="text-2xl font-bold text-zinc-900">Studio Mode</h2>
                <p className="text-zinc-500">Manual asset generation and batch processing.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ImageGenerator />
                <VideoGenerator />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <BatchProcessor />
                <Gallery />
            </div>
        </div>
    );
}
