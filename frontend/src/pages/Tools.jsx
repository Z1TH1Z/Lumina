import { useState } from 'react'
import client from '../api/client'
import {
    Wrench, Calculator, DollarSign, Home, PiggyBank,
    Play, Loader2, ChevronDown, ChevronUp,
} from 'lucide-react'

const TOOL_CONFIGS = {
    compound_interest: {
        icon: DollarSign,
        color: 'emerald',
        fields: [
            { name: 'principal', label: 'Principal ($)', type: 'number', placeholder: '10000' },
            { name: 'annual_rate', label: 'Annual Rate (%)', type: 'number', placeholder: '7', step: '0.1' },
            { name: 'years', label: 'Years', type: 'number', placeholder: '10' },
            { name: 'compounds_per_year', label: 'Compounds/Year', type: 'number', placeholder: '12' },
        ],
    },
    loan_amortization: {
        icon: Home,
        color: 'sky',
        fields: [
            { name: 'principal', label: 'Loan Amount ($)', type: 'number', placeholder: '250000' },
            { name: 'annual_rate', label: 'Annual Rate (%)', type: 'number', placeholder: '6.5', step: '0.1' },
            { name: 'years', label: 'Loan Term (Years)', type: 'number', placeholder: '30' },
        ],
    },
    tax_estimate: {
        icon: Calculator,
        color: 'amber',
        fields: [
            { name: 'gross_income', label: 'Gross Income ($)', type: 'number', placeholder: '85000' },
            { name: 'deductions', label: 'Deductions ($)', type: 'number', placeholder: '14600' },
            { name: 'filing_status', label: 'Filing Status', type: 'select', options: ['single', 'married'] },
        ],
    },
    savings_goal: {
        icon: PiggyBank,
        color: 'primary',
        fields: [
            { name: 'target_amount', label: 'Target ($)', type: 'number', placeholder: '100000' },
            { name: 'current_savings', label: 'Current Savings ($)', type: 'number', placeholder: '5000' },
            { name: 'monthly_contribution', label: 'Monthly Contribution ($)', type: 'number', placeholder: '500' },
            { name: 'annual_return', label: 'Annual Return (%)', type: 'number', placeholder: '7', step: '0.1' },
        ],
    },
}

export default function Tools() {
    const [selectedTool, setSelectedTool] = useState(null)
    const [formData, setFormData] = useState({})
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [availableTools, setAvailableTools] = useState([])
    const [customCode, setCustomCode] = useState('')
    const [customResult, setCustomResult] = useState(null)

    const runTool = async (toolName) => {
        setLoading(true)
        setResult(null)

        // Convert string values to numbers
        const params = {}
        for (const [key, val] of Object.entries(formData)) {
            const config = TOOL_CONFIGS[toolName]?.fields.find((f) => f.name === key)
            if (config?.type === 'number') {
                params[key] = parseFloat(val) || 0
            } else {
                params[key] = val
            }
        }

        try {
            const res = await client.post('/api/v1/tools/execute', {
                tool_name: toolName,
                parameters: params,
            })
            setResult(res.data)
        } catch (err) {
            setResult({ error: err.response?.data?.detail || 'Execution failed' })
        } finally {
            setLoading(false)
        }
    }

    const runCustom = async () => {
        setLoading(true)
        try {
            const res = await client.post('/api/v1/tools/calculate', {
                code: customCode,
                variables: {},
            })
            setCustomResult(res.data)
        } catch (err) {
            setCustomResult({ success: false, error: err.response?.data?.detail || 'Failed' })
        } finally {
            setLoading(false)
        }
    }

    const colorMap = {
        emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        sky: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
        amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        primary: 'bg-primary-500/10 text-primary-400 border-primary-500/20',
    }

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="page-title">Financial Tools</h1>
                <p className="page-subtitle">Deterministic financial calculators</p>
            </div>

            {/* Tool Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                {Object.entries(TOOL_CONFIGS).map(([name, config]) => {
                    const Icon = config.icon
                    const isSelected = selectedTool === name
                    const colors = colorMap[config.color]

                    return (
                        <div key={name} className="glass-card overflow-hidden">
                            <button
                                onClick={() => {
                                    setSelectedTool(isSelected ? null : name)
                                    setFormData({})
                                    setResult(null)
                                }}
                                className="w-full p-5 flex items-center justify-between hover:bg-white/5 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <div className={`p-3 rounded-xl ${colors.split(' ')[0]}`}>
                                        <Icon className={`w-5 h-5 ${colors.split(' ')[1]}`} />
                                    </div>
                                    <div className="text-left">
                                        <p className="font-medium">
                                            {name.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                                        </p>
                                        <p className="text-xs text-surface-200/40 mt-0.5">
                                            {name === 'compound_interest' && 'Calculate investment growth'}
                                            {name === 'loan_amortization' && 'Generate payment schedule'}
                                            {name === 'tax_estimate' && 'Estimate federal income tax'}
                                            {name === 'savings_goal' && 'Plan your savings timeline'}
                                        </p>
                                    </div>
                                </div>
                                {isSelected ? (
                                    <ChevronUp className="w-5 h-5 text-surface-200/40" />
                                ) : (
                                    <ChevronDown className="w-5 h-5 text-surface-200/40" />
                                )}
                            </button>

                            {isSelected && (
                                <div className="px-5 pb-5 animate-slide-up">
                                    <div className="space-y-3 mt-2">
                                        {config.fields.map((field) => (
                                            <div key={field.name}>
                                                <label className="text-xs font-medium text-surface-200/50 mb-1 block">
                                                    {field.label}
                                                </label>
                                                {field.type === 'select' ? (
                                                    <select
                                                        value={formData[field.name] || field.options[0]}
                                                        onChange={(e) =>
                                                            setFormData((prev) => ({ ...prev, [field.name]: e.target.value }))
                                                        }
                                                        className="input-field py-2 text-sm"
                                                    >
                                                        {field.options.map((opt) => (
                                                            <option key={opt} value={opt}>
                                                                {opt.charAt(0).toUpperCase() + opt.slice(1)}
                                                            </option>
                                                        ))}
                                                    </select>
                                                ) : (
                                                    <input
                                                        type={field.type}
                                                        step={field.step}
                                                        placeholder={field.placeholder}
                                                        value={formData[field.name] || ''}
                                                        onChange={(e) =>
                                                            setFormData((prev) => ({ ...prev, [field.name]: e.target.value }))
                                                        }
                                                        className="input-field py-2 text-sm"
                                                    />
                                                )}
                                            </div>
                                        ))}

                                        <button
                                            onClick={() => runTool(name)}
                                            disabled={loading}
                                            className="btn-primary w-full flex items-center justify-center gap-2"
                                        >
                                            {loading ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <Play className="w-4 h-4" />
                                            )}
                                            Calculate
                                        </button>

                                        {result?.result && (
                                            <div className="mt-4 p-4 rounded-xl bg-white/5 border border-white/5 space-y-2 animate-fade-in">
                                                {Object.entries(result.result).map(([key, val]) => {
                                                    if (key === 'schedule_summary') return null
                                                    return (
                                                        <div key={key} className="flex justify-between text-sm">
                                                            <span className="text-surface-200/50">
                                                                {key.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                                                            </span>
                                                            <span className="font-medium font-mono">
                                                                {typeof val === 'number'
                                                                    ? key.includes('rate') || key.includes('years')
                                                                        ? val
                                                                        : `$${val.toLocaleString()}`
                                                                    : String(val)}
                                                            </span>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}

                                        {result?.error && (
                                            <div className="mt-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
                                                {result.error}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Custom Calculation */}
            <div className="glass-card p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Wrench className="w-5 h-5 text-primary-400" />
                    Custom Calculation (Sandbox)
                </h3>
                <p className="text-sm text-surface-200/40 mb-4">
                    Write Python code for custom financial calculations. Runs in a secure sandbox.
                </p>
                <textarea
                    value={customCode}
                    onChange={(e) => setCustomCode(e.target.value)}
                    placeholder={`# Example:\nprincipal = 10000\nrate = 0.07\nyears = 10\nresult = principal * (1 + rate) ** years`}
                    className="input-field font-mono text-sm h-32 resize-y"
                />
                <button
                    onClick={runCustom}
                    disabled={loading || !customCode.trim()}
                    className="btn-primary mt-3 flex items-center gap-2"
                >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Run
                </button>

                {customResult && (
                    <div className={`mt-4 p-4 rounded-xl border ${customResult.success ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'
                        } animate-fade-in`}>
                        {customResult.success ? (
                            <pre className="text-sm font-mono text-surface-200/70 whitespace-pre-wrap">
                                {JSON.stringify(customResult.result, null, 2)}
                            </pre>
                        ) : (
                            <p className="text-sm text-rose-400">{customResult.error}</p>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}
