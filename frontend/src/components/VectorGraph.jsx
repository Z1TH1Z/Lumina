import React, { useRef, useMemo, useEffect, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import api from '../api/client';
import { useAuth } from '../context/AuthContext';
import useMeasure from 'react-use-measure';

const VectorGraph = ({ onNodeClick }) => {
    const fgRef = useRef();
    const [graphData, setGraphData] = useState({ nodes: [], links: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { user } = useAuth();
    const [containerRef, bounds] = useMeasure();

    useEffect(() => {
        const fetchNodes = async () => {
            try {
                const response = await api.get('/api/v1/rag/nodes');
                setGraphData(response.data);
            } catch (err) {
                console.error("Failed to load graph nodes", err);
                setError(err.message || 'Failed to load brain map');
            } finally {
                setLoading(false);
            }
        };
        if (user) {
            fetchNodes();
        }
    }, [user]);

    const groupColors = useMemo(() => ({
        user: '#8b5cf6', // Violet
        category: '#3b82f6', // Blue
        transaction: '#ef4444', // Red
        ai: '#10b981', // Emerald
        document: '#f59e0b', // Amber
    }), []);

    if (loading) {
        return <div className="flex justify-center items-center h-full w-full bg-slate-900 rounded-lg text-slate-400">Initializing Brain Visualizer...</div>;
    }

    if (error) {
        return <div className="flex justify-center items-center h-full w-full bg-slate-900 rounded-lg text-rose-400">Error: {error}</div>;
    }

    return (
        <div ref={containerRef} className="w-full h-full rounded-lg overflow-hidden border border-slate-700 bg-slate-900 relative">
            <div className="absolute top-4 left-4 z-10 bg-slate-800/80 backdrop-blur-sm border border-slate-700 rounded-md p-3 text-xs text-slate-300 pointer-events-none">
                <h3 className="font-semibold text-white mb-2 text-sm text-balance">Vector Space</h3>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-violet-500 block"></span> You</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-blue-500 block"></span> Categories</div>
                <div className="flex items-center gap-2 mb-1"><span className="w-3 h-3 rounded-full bg-red-500 block"></span> Transactions</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-emerald-500 block"></span> AI Memory</div>
            </div>

            {bounds.width > 0 && bounds.height > 0 && graphData.nodes && graphData.nodes.length > 0 && (
                <ForceGraph3D
                    width={bounds.width}
                    height={bounds.height}
                    ref={fgRef}
                    graphData={graphData}
                    nodeLabel="name"
                    nodeColor={node => groupColors[node.group] || '#999'}
                    nodeVal={node => node.val || 1}
                    linkColor={() => '#475569'}
                    linkOpacity={0.3}
                    linkWidth={1}
                    nodeResolution={16}
                    backgroundColor="#0f172a"
                    onNodeClick={(node) => {
                        if (!node || !node.x || !node.y || !node.z) return;
                        const distance = 40;
                        const distRatio = 1 + distance / Math.hypot(node.x, node.y, node.z);
                        if (fgRef.current) {
                            fgRef.current.cameraPosition(
                                { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
                                node,
                                3000
                            );
                        }
                        if (onNodeClick) onNodeClick(node);
                    }}
                    showNavInfo={false}
                />
            )}
        </div>
    );
};

export default VectorGraph;

