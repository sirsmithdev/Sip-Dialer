import { Link } from 'react-router-dom';
import {
  Phone,
  MessageSquare,
  Zap,
  Shield,
  BarChart3,
  Code,
  CheckCircle,
  ArrowRight,
  Play,
  Globe,
  Clock,
  Users,
  Headphones,
  Send,
  Webhook,
  Key,
  FileJson,
  ChevronRight,
  Star,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b bg-background/80 backdrop-blur-md">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
                <Phone className="h-4 w-4 text-white" />
              </div>
              <span className="text-xl font-bold">CallFlow</span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Features
              </a>
              <a href="#api" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                API
              </a>
              <a href="#pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Pricing
              </a>
              <a href="#docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Docs
              </a>
            </div>
            <div className="flex items-center gap-4">
              <Link to="/login">
                <Button variant="ghost" size="sm">
                  Sign In
                </Button>
              </Link>
              <Link to="/login">
                <Button size="sm" className="gradient-primary border-0">
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 gradient-mesh text-white overflow-hidden">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8 animate-fade-in">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-sm">
                <Zap className="h-4 w-4 text-yellow-400" />
                <span>Now with SMS Gateway API</span>
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
                Automate Your
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
                  Voice & SMS
                </span>
                Communications
              </h1>
              <p className="text-lg text-gray-300 max-w-xl">
                Enterprise-grade auto-dialer and SMS gateway platform. Reach thousands of customers
                with automated voice campaigns and integrate SMS into your apps with our powerful API.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link to="/login">
                  <Button size="lg" className="bg-white text-slate-900 hover:bg-gray-100">
                    Start Free Trial
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10">
                  <Play className="mr-2 h-5 w-5" />
                  Watch Demo
                </Button>
              </div>
              <div className="flex items-center gap-8 pt-4">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-400" />
                  <span className="text-sm text-gray-300">No credit card required</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-400" />
                  <span className="text-sm text-gray-300">14-day free trial</span>
                </div>
              </div>
            </div>
            <div className="relative hidden lg:block">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-3xl blur-3xl" />
              <div className="relative glass rounded-3xl p-8 animate-float">
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5">
                    <div className="h-10 w-10 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Phone className="h-5 w-5 text-green-400" />
                    </div>
                    <div>
                      <p className="font-medium">Campaign Started</p>
                      <p className="text-sm text-gray-400">2,500 contacts queued</p>
                    </div>
                    <Badge className="ml-auto bg-green-500/20 text-green-400 border-0">Active</Badge>
                  </div>
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5">
                    <div className="h-10 w-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <MessageSquare className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="font-medium">SMS Sent</p>
                      <p className="text-sm text-gray-400">1,847 delivered</p>
                    </div>
                    <Badge className="ml-auto bg-blue-500/20 text-blue-400 border-0">98.2%</Badge>
                  </div>
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5">
                    <div className="h-10 w-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <BarChart3 className="h-5 w-5 text-purple-400" />
                    </div>
                    <div>
                      <p className="font-medium">Answer Rate</p>
                      <p className="text-sm text-gray-400">Above average</p>
                    </div>
                    <Badge className="ml-auto bg-purple-500/20 text-purple-400 border-0">42.3%</Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 border-b">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: '50M+', label: 'Calls Made', icon: Phone },
              { value: '100M+', label: 'SMS Delivered', icon: MessageSquare },
              { value: '99.9%', label: 'Uptime SLA', icon: Shield },
              { value: '5,000+', label: 'Active Users', icon: Users },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <stat.icon className="h-8 w-8 mx-auto mb-2 text-primary" />
                <p className="text-3xl font-bold">{stat.value}</p>
                <p className="text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="outline" className="mb-4">Features</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Two Powerful Platforms, One Solution
            </h2>
            <p className="text-lg text-muted-foreground">
              Whether you need automated voice campaigns or programmable SMS, CallFlow has you covered
              with enterprise-grade reliability and developer-friendly APIs.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            {/* Auto-Dialer Card */}
            <Card className="relative overflow-hidden border-2 hover:border-primary/50 transition-colors">
              <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-blue-500/10 to-transparent rounded-full -translate-y-32 translate-x-32" />
              <CardContent className="p-8">
                <div className="h-14 w-14 rounded-2xl gradient-primary flex items-center justify-center mb-6">
                  <Phone className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3">Auto-Dialer Platform</h3>
                <p className="text-muted-foreground mb-6">
                  Launch automated voice campaigns at scale. Perfect for appointment reminders,
                  surveys, notifications, and outbound sales.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    'Visual IVR flow builder',
                    'Predictive & progressive dialing',
                    'Real-time campaign analytics',
                    'CRM integrations',
                    'Call recording & transcription',
                    'Custom caller ID management',
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button className="w-full gradient-primary border-0">
                  Explore Auto-Dialer
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>

            {/* SMS Gateway Card */}
            <Card className="relative overflow-hidden border-2 hover:border-primary/50 transition-colors">
              <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-cyan-500/10 to-transparent rounded-full -translate-y-32 translate-x-32" />
              <CardContent className="p-8">
                <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center mb-6">
                  <MessageSquare className="h-7 w-7 text-white" />
                </div>
                <h3 className="text-2xl font-bold mb-3">SMS Gateway API</h3>
                <p className="text-muted-foreground mb-6">
                  Programmable SMS API for developers. Send transactional messages, OTPs,
                  marketing campaigns, and two-way conversations.
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    'RESTful API & webhooks',
                    'Global carrier coverage',
                    'Two-way messaging support',
                    'Message scheduling',
                    'Delivery reports & analytics',
                    'Template management',
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-3">
                      <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button variant="outline" className="w-full">
                  View API Docs
                  <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* API Section */}
      <section id="api" className="py-20 bg-slate-950 text-white">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <Badge variant="outline" className="border-white/20 text-white">
                Developer-First
              </Badge>
              <h2 className="text-3xl sm:text-4xl font-bold">
                Powerful APIs for Voice & SMS
              </h2>
              <p className="text-gray-400 text-lg">
                Integrate communication capabilities into your applications in minutes.
                Our RESTful APIs are designed for developers, with comprehensive SDKs
                and detailed documentation.
              </p>
              <div className="grid sm:grid-cols-2 gap-4">
                {[
                  { icon: Webhook, title: 'Webhooks', desc: 'Real-time event notifications' },
                  { icon: Key, title: 'API Keys', desc: 'Secure authentication' },
                  { icon: FileJson, title: 'JSON/REST', desc: 'Modern API standards' },
                  { icon: Code, title: 'SDKs', desc: 'Python, Node, PHP, Ruby' },
                ].map((item) => (
                  <div key={item.title} className="flex items-start gap-3 p-4 rounded-lg bg-white/5">
                    <item.icon className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <p className="font-medium">{item.title}</p>
                      <p className="text-sm text-gray-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="relative">
              <Tabs defaultValue="sms" className="w-full">
                <TabsList className="w-full bg-white/5 border border-white/10">
                  <TabsTrigger value="sms" className="flex-1 data-[state=active]:bg-primary">
                    Send SMS
                  </TabsTrigger>
                  <TabsTrigger value="voice" className="flex-1 data-[state=active]:bg-primary">
                    Make Call
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="sms" className="mt-4">
                  <div className="rounded-lg bg-slate-900 border border-white/10 overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10">
                      <div className="h-3 w-3 rounded-full bg-red-500" />
                      <div className="h-3 w-3 rounded-full bg-yellow-500" />
                      <div className="h-3 w-3 rounded-full bg-green-500" />
                      <span className="ml-2 text-xs text-gray-500">send_sms.py</span>
                    </div>
                    <pre className="p-4 text-sm overflow-x-auto">
                      <code className="text-gray-300">
{`import callflow

client = callflow.Client(api_key="your_api_key")

# Send an SMS message
message = client.sms.send(
    to="+1234567890",
    from_="+1987654321",
    body="Your verification code is 123456"
)

print(f"Message SID: {message.sid}")
print(f"Status: {message.status}")`}
                      </code>
                    </pre>
                  </div>
                </TabsContent>
                <TabsContent value="voice" className="mt-4">
                  <div className="rounded-lg bg-slate-900 border border-white/10 overflow-hidden">
                    <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10">
                      <div className="h-3 w-3 rounded-full bg-red-500" />
                      <div className="h-3 w-3 rounded-full bg-yellow-500" />
                      <div className="h-3 w-3 rounded-full bg-green-500" />
                      <span className="ml-2 text-xs text-gray-500">make_call.py</span>
                    </div>
                    <pre className="p-4 text-sm overflow-x-auto">
                      <code className="text-gray-300">
{`import callflow

client = callflow.Client(api_key="your_api_key")

# Initiate an outbound call
call = client.calls.create(
    to="+1234567890",
    from_="+1987654321",
    ivr_flow_id="flow_abc123",
    webhook_url="https://your-app.com/webhook"
)

print(f"Call SID: {call.sid}")
print(f"Status: {call.status}")`}
                      </code>
                    </pre>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="outline" className="mb-4">Use Cases</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Built for Every Industry
            </h2>
            <p className="text-lg text-muted-foreground">
              From healthcare to finance, our platform powers communication for businesses of all sizes.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Headphones,
                title: 'Customer Service',
                description: 'Automated callbacks, satisfaction surveys, and support notifications.',
              },
              {
                icon: Clock,
                title: 'Appointment Reminders',
                description: 'Reduce no-shows with automated voice and SMS reminders.',
              },
              {
                icon: Shield,
                title: 'Two-Factor Auth',
                description: 'Secure your apps with SMS OTP verification.',
              },
              {
                icon: Send,
                title: 'Marketing Campaigns',
                description: 'Reach customers with promotional voice and text messages.',
              },
              {
                icon: Globe,
                title: 'Global Notifications',
                description: 'Deliver critical alerts worldwide with high deliverability.',
              },
              {
                icon: BarChart3,
                title: 'Surveys & Feedback',
                description: 'Collect responses via interactive voice and SMS surveys.',
              },
            ].map((useCase) => (
              <Card key={useCase.title} className="card-hover">
                <CardContent className="p-6">
                  <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                    <useCase.icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{useCase.title}</h3>
                  <p className="text-sm text-muted-foreground">{useCase.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-muted/30">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="outline" className="mb-4">Pricing</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-lg text-muted-foreground">
              Pay only for what you use. No hidden fees, no long-term contracts.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Starter Plan */}
            <Card className="relative">
              <CardContent className="p-8">
                <h3 className="text-xl font-bold mb-2">Starter</h3>
                <p className="text-muted-foreground mb-4">For small teams getting started</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold">$49</span>
                  <span className="text-muted-foreground">/month</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {[
                    '1,000 voice minutes',
                    '5,000 SMS messages',
                    '1 phone number',
                    'Basic analytics',
                    'Email support',
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button variant="outline" className="w-full">Get Started</Button>
              </CardContent>
            </Card>

            {/* Professional Plan */}
            <Card className="relative border-2 border-primary">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <Badge className="gradient-primary border-0">Most Popular</Badge>
              </div>
              <CardContent className="p-8">
                <h3 className="text-xl font-bold mb-2">Professional</h3>
                <p className="text-muted-foreground mb-4">For growing businesses</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold">$199</span>
                  <span className="text-muted-foreground">/month</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {[
                    '10,000 voice minutes',
                    '50,000 SMS messages',
                    '5 phone numbers',
                    'Advanced analytics',
                    'API access',
                    'Priority support',
                    'Webhooks',
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button className="w-full gradient-primary border-0">Get Started</Button>
              </CardContent>
            </Card>

            {/* Enterprise Plan */}
            <Card className="relative">
              <CardContent className="p-8">
                <h3 className="text-xl font-bold mb-2">Enterprise</h3>
                <p className="text-muted-foreground mb-4">For large organizations</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold">Custom</span>
                </div>
                <ul className="space-y-3 mb-8">
                  {[
                    'Unlimited voice minutes',
                    'Unlimited SMS messages',
                    'Unlimited phone numbers',
                    'Custom integrations',
                    'Dedicated account manager',
                    '24/7 phone support',
                    'SLA guarantee',
                  ].map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      {feature}
                    </li>
                  ))}
                </ul>
                <Button variant="outline" className="w-full">Contact Sales</Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="outline" className="mb-4">Testimonials</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Trusted by Thousands
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                quote: "CallFlow's auto-dialer reduced our no-show rate by 40%. The visual IVR builder is incredibly intuitive.",
                author: 'Sarah Johnson',
                role: 'Operations Manager',
                company: 'HealthFirst Clinic',
              },
              {
                quote: "We integrated the SMS API in less than a day. The documentation is excellent and the delivery rates are outstanding.",
                author: 'Michael Chen',
                role: 'Lead Developer',
                company: 'TechStart Inc',
              },
              {
                quote: "The analytics dashboard gives us complete visibility into our campaigns. Best ROI we've seen from any communication tool.",
                author: 'Emily Rodriguez',
                role: 'Marketing Director',
                company: 'RetailPro',
              },
            ].map((testimonial) => (
              <Card key={testimonial.author} className="card-hover">
                <CardContent className="p-6">
                  <div className="flex gap-1 mb-4">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star key={star} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                    ))}
                  </div>
                  <p className="text-muted-foreground mb-6">"{testimonial.quote}"</p>
                  <div>
                    <p className="font-semibold">{testimonial.author}</p>
                    <p className="text-sm text-muted-foreground">
                      {testimonial.role}, {testimonial.company}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 gradient-mesh text-white">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Ready to Transform Your Communications?
          </h2>
          <p className="text-lg text-gray-300 mb-8 max-w-2xl mx-auto">
            Join thousands of businesses using CallFlow to automate their voice and SMS communications.
            Start your free trial today.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/login">
              <Button size="lg" className="bg-white text-slate-900 hover:bg-gray-100">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Button size="lg" variant="outline" className="border-white/20 text-white hover:bg-white/10">
              Schedule Demo
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="h-8 w-8 rounded-lg gradient-primary flex items-center justify-center">
                  <Phone className="h-4 w-4 text-white" />
                </div>
                <span className="text-xl font-bold">CallFlow</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Enterprise-grade voice and SMS communication platform for modern businesses.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Auto-Dialer</a></li>
                <li><a href="#" className="hover:text-foreground">SMS Gateway</a></li>
                <li><a href="#" className="hover:text-foreground">IVR Builder</a></li>
                <li><a href="#" className="hover:text-foreground">Analytics</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Developers</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">API Documentation</a></li>
                <li><a href="#" className="hover:text-foreground">SDKs</a></li>
                <li><a href="#" className="hover:text-foreground">Webhooks</a></li>
                <li><a href="#" className="hover:text-foreground">Status Page</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">About</a></li>
                <li><a href="#" className="hover:text-foreground">Blog</a></li>
                <li><a href="#" className="hover:text-foreground">Careers</a></li>
                <li><a href="#" className="hover:text-foreground">Contact</a></li>
              </ul>
            </div>
          </div>
          <div className="pt-8 border-t flex flex-col sm:flex-row justify-between items-center gap-4">
            <p className="text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} CallFlow. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <a href="#" className="hover:text-foreground">Privacy Policy</a>
              <a href="#" className="hover:text-foreground">Terms of Service</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
