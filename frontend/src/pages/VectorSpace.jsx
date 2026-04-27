import React from 'react';
import { Network } from 'lucide-react';
import VectorGraph from '../components/VectorGraph';

export default function VectorSpace() {
    return (
        <div className="page-container h-screen max-h-screen flex flex-col overflow-hidden">
            <div className="page-header shrink-0 pb-4 border-b border-white/5 mb-4">
                <h1 className="page-title flex items-center gap-2">
                    <Network className="w-7 h-7 text-primary-400" />
                    Vector Space
                </h1>
                <p className="page-subtitle">Interactive 3D visualization of your financial data</p>
            </div>

            <div className="flex-1 w-full relative min-h-[500px]">
                {/* VectorGraph expands to fill parent bounds using react-use-measure */}
                <VectorGraph />
            </div>
        </div>
    );
}
