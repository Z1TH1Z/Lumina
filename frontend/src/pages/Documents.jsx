import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import client from '../api/client'
import { FileText, Upload, Trash2, Clock, CheckCircle, XCircle, Loader2, Lock, Eye, EyeOff, ShieldCheck, AlertTriangle } from 'lucide-react'

export default function Documents() {
    const [documents, setDocuments] = useState([])
    const [uploading, setUploading] = useState(false)
    const [uploadResult, setUploadResult] = useState(null)

    // Encryption / password modal state
    const [showPasswordModal, setShowPasswordModal] = useState(false)
    const [pendingFileId, setPendingFileId] = useState(null)
    const [pendingFilename, setPendingFilename] = useState(null)
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [passwordError, setPasswordError] = useState(null)
    const [decrypting, setDecrypting] = useState(false)

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

    const processUpload = async (fileId, filename, pwd) => {
        /**
         * Upload using a staged file_id (from check-encryption) or re-send
         * the file.  Password is sent as a Form field and is never persisted.
         */
        const formData = new FormData()
        formData.append('file_id', fileId)
        formData.append('original_filename', filename)
        if (pwd) {
            formData.append('password', pwd)
        }

        const res = await client.post('/api/v1/documents/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
        return res
    }

    const onDrop = useCallback(async (acceptedFiles) => {
        if (acceptedFiles.length === 0) return

        setUploading(true)
        setUploadResult(null)

        for (const file of acceptedFiles) {
            const isPdf = file.type === 'application/pdf'

            if (isPdf) {
                // ── Step 1: Check encryption ───────────────────────────
                try {
                    const checkForm = new FormData()
                    checkForm.append('file', file)

                    const checkRes = await client.post(
                        '/api/v1/documents/check-encryption',
                        checkForm,
                        { headers: { 'Content-Type': 'multipart/form-data' } },
                    )

                    const { encrypted, file_id, filename } = checkRes.data

                    if (encrypted) {
                        // Show password modal — pause the loop
                        setPendingFileId(file_id)
                        setPendingFilename(filename)
                        setPassword('')
                        setPasswordError(null)
                        setShowPasswordModal(true)
                        setUploading(false)
                        return // exit; the modal's submit handler continues
                    }

                    // Not encrypted → process immediately
                    const res = await processUpload(file_id, filename, null)
                    setUploadResult({ success: true, message: res.data.message })
                } catch (err) {
                    setUploadResult({
                        success: false,
                        message: err.response?.data?.detail || 'Upload failed',
                    })
                }
            } else {
                // Non-PDF files go through direct upload
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
        }

        setUploading(false)
        fetchDocuments()
    }, [])

    const handlePasswordSubmit = async (e) => {
        e.preventDefault()
        if (!password.trim()) {
            setPasswordError('Password is required')
            return
        }

        setDecrypting(true)
        setPasswordError(null)

        try {
            const res = await processUpload(pendingFileId, pendingFilename, password)

            if (res.data.status === 'failed') {
                setPasswordError(res.data.message || 'Incorrect password. Please try again.')
                setDecrypting(false)
                return
            }

            // Success
            setShowPasswordModal(false)
            setUploadResult({ success: true, message: res.data.message })
            setPassword('')
            setPendingFileId(null)
            setPendingFilename(null)
            fetchDocuments()
        } catch (err) {
            setPasswordError(
                err.response?.data?.detail || err.response?.data?.message || 'Decryption failed. Please check your password.',
            )
        } finally {
            setDecrypting(false)
        }
    }

    const cancelPasswordModal = () => {
        setShowPasswordModal(false)
        setPassword('')
        setPasswordError(null)
        setPendingFileId(null)
        setPendingFilename(null)
    }

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'application/pdf': ['.pdf'],
            'image/png': ['.png'],
            'image/jpeg': ['.jpg', '.jpeg'],
            'text/markdown': ['.md'],
            'text/plain': ['.txt'],
            'application/vnd.ms-excel': ['.xls'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
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
                            PDF, PNG, JPG, MD, TXT, XLS(X) up to 50MB · Bank statements, invoices, receipts
                        </p>
                        <p className="text-xs text-surface-200/30 mt-2 flex items-center justify-center gap-1.5">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            Encrypted PDFs supported — password never stored
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

            {/* ── Password Modal ──────────────────────────────────────── */}
            {showPasswordModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
                    <div className="glass-card w-full max-w-md mx-4 p-0 overflow-hidden shadow-2xl border border-white/10">
                        {/* Header */}
                        <div className="px-6 pt-6 pb-4 border-b border-white/5">
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
                                    <Lock className="w-5 h-5 text-amber-400" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold">Encrypted PDF</h3>
                                    <p className="text-sm text-surface-200/40">Password required to extract data</p>
                                </div>
                            </div>
                            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 text-sm">
                                <FileText className="w-4 h-4 text-primary-400 flex-shrink-0" />
                                <span className="truncate text-surface-200/60">{pendingFilename}</span>
                            </div>
                        </div>

                        {/* Form */}
                        <form onSubmit={handlePasswordSubmit} className="px-6 py-5 space-y-4">
                            <div>
                                <label htmlFor="pdf-password" className="block text-sm font-medium text-surface-200/60 mb-2">
                                    PDF Password
                                </label>
                                <div className="relative">
                                    <input
                                        id="pdf-password"
                                        type={showPassword ? 'text' : 'password'}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter document password"
                                        autoFocus
                                        className="w-full px-4 py-3 pr-12 rounded-xl bg-white/5 border border-white/10 text-white placeholder-surface-200/30 focus:outline-none focus:border-primary-500/50 focus:ring-1 focus:ring-primary-500/20 transition-all"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-surface-200/30 hover:text-surface-200/60 transition-colors"
                                        tabIndex={-1}
                                    >
                                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                    </button>
                                </div>
                            </div>

                            {/* Error Message */}
                            {passwordError && (
                                <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm animate-slide-up">
                                    <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                                    <span>{passwordError}</span>
                                </div>
                            )}

                            {/* Security note */}
                            <div className="flex items-center gap-2 text-xs text-surface-200/30">
                                <ShieldCheck className="w-3.5 h-3.5" />
                                <span>Your password is used only for decryption and is never stored</span>
                            </div>

                            {/* Actions */}
                            <div className="flex gap-3 pt-1">
                                <button
                                    type="button"
                                    onClick={cancelPasswordModal}
                                    className="flex-1 px-4 py-2.5 rounded-xl border border-white/10 text-surface-200/60 hover:bg-white/5 transition-all text-sm font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={decrypting || !password.trim()}
                                    className="flex-1 px-4 py-2.5 rounded-xl bg-primary-500 hover:bg-primary-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium transition-all flex items-center justify-center gap-2"
                                >
                                    {decrypting ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Decrypting…
                                        </>
                                    ) : (
                                        <>
                                            <Lock className="w-4 h-4" />
                                            Unlock & Process
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
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
