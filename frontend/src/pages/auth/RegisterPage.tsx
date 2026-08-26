import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuth';
import { Eye, EyeOff } from 'lucide-react';

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { register: registerUser } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    password_confirm: '',
    full_name: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    if (formData.password !== formData.password_confirm) {
      setError(t('auth.passwordsMustMatch'));
      setIsLoading(false);
      return;
    }

    try {
      const result = await registerUser({
        email: formData.email,
        username: formData.email.split('@')[0],
        password: formData.password,
        full_name: formData.full_name,
      });
      if (result.success) {
        setMessage(result.message || t('auth.registerSuccess'));
        setTimeout(() => navigate('/login'), 2500);
      } else {
        setError(result.error || t('auth.registrationFailed'));
      }
    } catch (err: any) {
      setError(err.message || t('auth.registrationFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5 card-lg">
      <h2 className="text-xl font-bold text-slate-900 mb-6">{t('auth.register')}</h2>

      {error && (
        <div className="alert alert-error text-sm">
          {error}
        </div>
      )}
      {message && (
        <div className="alert alert-success text-sm">
          {message}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.fullName')}
        </label>
        <input
          type="text"
          name="full_name"
          value={formData.full_name}
          onChange={handleChange}
          className="input-base"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.email')}
        </label>
        <input
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          className="input-base"
          required
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.password')}
        </label>
        <div className="relative">
          <input
            type={showPassword ? 'text' : 'password'}
            name="password"
            value={formData.password}
            onChange={handleChange}
            className="input-base pr-10"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          {t('auth.confirmPassword')}
        </label>
        <div className="relative">
          <input
            type={showPasswordConfirm ? 'text' : 'password'}
            name="password_confirm"
            value={formData.password_confirm}
            onChange={handleChange}
            className="input-base pr-10"
            required
          />
          <button
            type="button"
            onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-500 hover:text-slate-700"
          >
            {showPasswordConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading || !!message}
        className="btn-primary w-full"
      >
        {isLoading ? t('common.loading') : t('auth.register')}
      </button>

      <div className="text-center text-sm">
        <span className="text-slate-600">{t('auth.haveAccount')} </span>
        <RouterLink to="/login" className="text-primary-600 hover:text-primary-700 font-medium">
          {t('auth.login')}
        </RouterLink>
      </div>
    </form>
  );
}
