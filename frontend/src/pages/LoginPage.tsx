import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Phone, Shield, Zap, BarChart3, Loader2 } from 'lucide-react';

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    try {
      await login({ email, password });
      navigate('/');
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 gradient-mesh relative overflow-hidden">
        {/* Floating decorative elements */}
        <div className="absolute top-20 left-20 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />

        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center">
              <Phone className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold">SIP Auto-Dialer</span>
          </div>

          {/* Headline */}
          <h1 className="text-4xl font-bold mb-6 leading-tight">
            Enterprise-Grade<br />
            <span className="text-purple-400">Outbound Calling</span><br />
            Platform
          </h1>

          <p className="text-gray-400 text-lg mb-12 max-w-md">
            Power your contact center with intelligent auto-dialing,
            real-time analytics, and seamless CRM integration.
          </p>

          {/* Features */}
          <div className="space-y-6">
            <div className="flex items-center gap-4 animate-fade-in" style={{ animationDelay: '0.2s' }}>
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold">High Performance</h3>
                <p className="text-sm text-gray-400">Handle thousands of concurrent calls</p>
              </div>
            </div>

            <div className="flex items-center gap-4 animate-fade-in" style={{ animationDelay: '0.4s' }}>
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold">Real-Time Analytics</h3>
                <p className="text-sm text-gray-400">Monitor campaigns with live dashboards</p>
              </div>
            </div>

            <div className="flex items-center gap-4 animate-fade-in" style={{ animationDelay: '0.6s' }}>
              <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <Shield className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold">Enterprise Security</h3>
                <p className="text-sm text-gray-400">End-to-end encryption & compliance</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md animate-fade-in">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
              <Phone className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold">SIP Auto-Dialer</span>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-2">Welcome back</h2>
            <p className="text-muted-foreground">
              Sign in to your account to continue
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800 animate-fade-in">
                {error}
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email" className="text-sm font-medium">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="h-12 px-4 bg-muted/50 border-border focus:border-primary focus:ring-primary"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <button
                  type="button"
                  className="text-sm text-primary hover:text-primary/80 transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="h-12 px-4 bg-muted/50 border-border focus:border-primary focus:ring-primary"
              />
            </div>

            <Button
              type="submit"
              className="w-full h-12 text-base font-semibold gradient-primary hover:opacity-90 transition-opacity"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign In'
              )}
            </Button>
          </form>

          <div className="mt-8 text-center text-sm text-muted-foreground">
            <p>
              Don't have an account?{' '}
              <button className="text-primary hover:text-primary/80 font-medium transition-colors">
                Contact administrator
              </button>
            </p>
          </div>

          {/* Footer */}
          <div className="mt-12 text-center text-xs text-muted-foreground">
            <p>Protected by enterprise-grade security</p>
          </div>
        </div>
      </div>
    </div>
  );
}
