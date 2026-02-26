import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import client from '../api/client'
import { FileText, Upload, Trash2, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react'

export default function Documents() {
    const [documents, setDocuments] = useState([])
    const [uploading, setUploading] = useState(false)
    const [uploadResult, setUploadResult] = useState(null)

    useEffect(() => {
        fetchDocuments()
    }, [])

    const fetchDocuments = async () => {
        try {
            const res = await client.get('/api/v1/documents/')
            setDocuments(res.data)
        } catch (err) {
            console.error('Failed to fetch documents:', err)
        }
    }

    const onDrop = useCallback(async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return

        setUploading(true)
        setUploadResult(null)

        for (const file of acceptedFiles) {
            const formData = new FormData()
            formData.append('file', file)

            try {
                const res = await client.post('/api/v1/documents/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                })
                setUploadResult({ success: true, message: res.data.message })
            } catch (err) {
                setUploadResult({
                    success: false,
                    message: err.response?.data?.detail || 'Upload failed',
                })
            }
        }

        setUploading(false)
        fetchDocuments()
    }, [])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
        },
        maxSize: 50 * 1024 * 1024,
    })

    const deleteDocument = async (id) => {
        try {
            await client.delete(`/api/v1/documents/${id}`)
            fetchDocuments()
        } catch (err) {
            console.error('Delete failed:', err)
        }
    }

    const statusConfig = {
        completed: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
        processing: { icon: Loader2, color: 'text-sky-400', bg: 'bg-sky-500/10' },
        pending: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
        failed: { icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-500/10' },
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="page-title">Documents</h1>
                <p className="page-subtitle">Upload and process financial documents</p>
            </div>

            {/* Upload Zone */}
            <div
                {...getRootProps()}
                className={`glass-card p-12 text-center cursor-pointer transition-all duration-300 mb-8 ${isDragActive
                    ? 'border-primary-500/50 bg-primary-500/5 scale-[1.01]'
                    : 'hover:border-white/20 hover:bg-white/5'
                    }`}
            >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center gap-4">
                    {uploading ? (
                        <Loader2 className="w-12 h-12 text-primary-400 animate-spin" />
                    ) : (
                        <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center">
                            <Upload className="w-8 h-8 text-primary-400" />
                        </div>
                    )}
                    <div>
                        <p className="text-lg font-medium">
                            {isDragActive ? 'Drop files here' : 'Drag & drop financial documents'}
                        </p>
                        <p className="text-sm text-surface-200/40 mt-1">
                            PDF, PNG, JPG up to 50MB · Bank statements, invoices, receipts
                        </p>
                    </div>
                </div>
            </div>

            {/* Upload Result */}
            {uploadResult && (
                <div
                    className={`mb-6 p-4 rounded-xl border ${uploadResult.success
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                        } animate-slide-up`}
                >
                    {uploadResult.message}
                </div>
            )}

            {/* Document List */}
            <div className="space-y-3">
                {documents.length === 0 ? (
                    <div className="glass-card p-12 text-center">
                        <FileText className="w-12 h-12 text-surface-200/20 mx-auto mb-3" />
                        <p className="text-surface-200/40">No documents uploaded yet</p>
                    </div>
                ) : (
                    documents.map((doc) => {
                        const status = statusConfig[doc.status] || statusConfig.pending
                        const StatusIcon = status.icon

                        return (
                            <div key={doc.id} className="glass-card-hover p-5 flex items-center justify-between">
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center">
                                        <FileText className="w-6 h-6 text-primary-400" />
                                    </div>
                                    <div>
                                        <p className="font-medium">{doc.original_filename}</p>
                                        <div className="flex items-center gap-3 mt-1 text-sm text-surface-200/40">
                                            <span>{doc.doc_type}</span>
                                            <span>·</span>
                                            <span>{doc.transaction_count} transactions</span>
                                            <span>·</span>
                                            <span>{doc.page_count || 0} pages</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3">
                                    <span className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium ${status.bg} ${status.color}`}>
                                        <StatusIcon className={`w-3.5 h-3.5 ${doc.status === 'processing' ? 'animate-spin' : ''}`} />
                                        {doc.status}
                                    </span>

                                    <button
                                        onClick={() => deleteDocument(doc.id)}
                                        className="p-2 rounded-lg hover:bg-rose-500/10 text-surface-200/30 hover:text-rose-400 transition-colors"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        )
                    })
                )}
            </div>
        </div>
    )
}
