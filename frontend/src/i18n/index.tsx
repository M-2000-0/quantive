/** Lightweight i18n — no external dependencies. */

export type Locale = 'en' | 'es' | 'fr' | 'pt';

const translations: Record<Locale, Record<string, string>> = {
  en: {
    // Navigation
    'nav.overview': 'Overview',
    'nav.portfolios': 'Debt Portfolio',
    'nav.optimization': 'Optimization',
    'nav.results': 'Results',
    'nav.benchmarks': 'Benchmarks',
    'nav.reports': 'Reports',
    'nav.audit': 'Audit Log',
    'nav.market': 'Market Data',
    'nav.advisor': 'AI Advisor',
    'nav.peers': 'Peers',
    'nav.whatif': 'What-If',
    'nav.riskIntel': 'Risk Intelligence',
    'nav.risk': 'Risk Dashboard',
    'nav.compliance': 'IMF Compliance',
    'nav.explain': 'Explainability',
    'nav.maturity': 'Maturity Ladder',
    'nav.esg': 'ESG / Green',
    'nav.ratings': 'Rating Simulator',
    'nav.security': 'Security',
    'nav.status': 'System Status',

    // Common
    'common.loading': 'Loading...',
    'common.save': 'Save',
    'common.cancel': 'Cancel',
    'common.delete': 'Delete',
    'common.edit': 'Edit',
    'common.search': 'Search...',
    'common.export': 'Export',
    'common.refresh': 'Refresh',
    'common.noData': 'No data available',
    'common.total': 'Total',
    'common.actions': 'Actions',
    'common.back': 'Back',
    'common.next': 'Next',
    'common.submit': 'Submit',

    // Dashboard
    'dashboard.title': 'Dashboard',
    'dashboard.welcome': 'Welcome to Quantive',
    'dashboard.portfolios': 'Portfolios',
    'dashboard.optimizations': 'Optimizations',
    'dashboard.totalDebt': 'Total Debt Managed',
    'dashboard.activeJobs': 'Active Jobs',

    // Portfolios
    'portfolio.title': 'Debt Portfolio',
    'portfolio.create': 'Create Portfolio',
    'portfolio.name': 'Portfolio Name',
    'portfolio.description': 'Description',
    'portfolio.instruments': 'Instruments',
    'portfolio.totalValue': 'Total Value',
    'portfolio.riskProfile': 'Risk Profile',

    // Optimization
    'optimization.title': 'Optimization Wizard',
    'optimization.selectPortfolio': 'Select Portfolio',
    'optimization.objective': 'Objective',
    'optimization.constraints': 'Constraints',
    'optimization.run': 'Run Optimization',
    'optimization.minimizeCost': 'Minimize Cost',
    'optimization.minimizeRisk': 'Minimize Risk',
    'optimization.maximizeReturn': 'Maximize Return',

    // Risk
    'risk.title': 'Risk Dashboard',
    'risk.score': 'Risk Score',
    'risk.var': 'Value at Risk',
    'risk.stress': 'Stress Testing',
    'risk.scenarios': 'Investment Scenarios',

    // Maturity
    'maturity.title': 'Debt Maturity Ladder',
    'maturity.smoothness': 'Smoothness',
    'maturity.walls': 'Maturity Walls',
    'maturity.recommendations': 'Refinancing Recommendations',

    // ESG
    'esg.title': 'ESG & Green Bond Analysis',
    'esg.score': 'ESG Score',
    'esg.green': 'Green Eligible',
    'esg.carbon': 'Carbon Risk',
    'esg.climate': 'Climate Rating',

    // Ratings
    'ratings.title': 'Rating Agency Simulator',
    'ratings.current': 'Current Rating',
    'ratings.simulated': 'Simulated Rating',
    'ratings.upgrade': 'Upgrade',
    'ratings.downgrade': 'Downgrade',
    'ratings.unchanged': 'Unchanged',

    // Compliance
    'compliance.title': 'IMF Compliance Reports',
    'compliance.dsa': 'Debt Sustainability Analysis',
    'compliance.mtds': 'Medium-Term Debt Strategy',
    'compliance.gfs': 'Government Finance Statistics',

    // Security
    'security.title': 'Security Dashboard',
    'security.score': 'Security Score',
    'security.threats': 'Threat Status',
    'security.users': 'User Accounts',

    // Auth
    'auth.login': 'Sign In',
    'auth.register': 'Create Account',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.forgotPassword': 'Forgot Password?',
    'auth.noAccount': "Don't have an account?",
    'auth.hasAccount': 'Already have an account?',

    // Marketplace
    'market.yieldCurve': 'Yield Curve',
    'market.fx': 'Exchange Rates',
    'market.rates': 'Interest Rates',
    'market.economic': 'Economic Indicators',
  },

  es: {
    'nav.overview': 'Resumen',
    'nav.portfolios': 'Cartera de Deuda',
    'nav.optimization': 'Optimizacion',
    'nav.results': 'Resultados',
    'nav.benchmarks': 'Comparativas',
    'nav.reports': 'Informes',
    'nav.audit': 'Registro de Auditoria',
    'nav.market': 'Datos de Mercado',
    'nav.advisor': 'Asesor IA',
    'nav.peers': 'Pares',
    'nav.whatif': 'Que Pasa Si',
    'nav.riskIntel': 'Inteligencia de Riesgo',
    'nav.risk': 'Panel de Riesgo',
    'nav.compliance': 'Cumplimiento FMI',
    'nav.explain': 'Explicabilidad',
    'nav.maturity': 'Escalon de Vencimiento',
    'nav.esg': 'ESG / Verde',
    'nav.ratings': 'Simulador de Calificacion',
    'nav.security': 'Seguridad',
    'nav.status': 'Estado del Sistema',

    'common.loading': 'Cargando...',
    'common.save': 'Guardar',
    'common.cancel': 'Cancelar',
    'common.delete': 'Eliminar',
    'common.edit': 'Editar',
    'common.search': 'Buscar...',
    'common.export': 'Exportar',
    'common.refresh': 'Actualizar',
    'common.noData': 'Sin datos disponibles',
    'common.total': 'Total',
    'common.actions': 'Acciones',
    'common.back': 'Atras',
    'common.next': 'Siguiente',
    'common.submit': 'Enviar',

    'dashboard.title': 'Panel',
    'dashboard.welcome': 'Bienvenido a Quantive',
    'dashboard.portfolios': 'Carteras',
    'dashboard.optimizations': 'Optimizaciones',
    'dashboard.totalDebt': 'Deuda Total Gestionada',
    'dashboard.activeJobs': 'Trabajos Activos',

    'portfolio.title': 'Cartera de Deuda',
    'portfolio.create': 'Crear Cartera',
    'portfolio.name': 'Nombre de Cartera',
    'portfolio.description': 'Descripcion',
    'portfolio.instruments': 'Instrumentos',
    'portfolio.totalValue': 'Valor Total',
    'portfolio.riskProfile': 'Perfil de Riesgo',

    'optimization.title': 'Asistente de Optimizacion',
    'optimization.selectPortfolio': 'Seleccionar Cartera',
    'optimization.objective': 'Objetivo',
    'optimization.constraints': 'Restricciones',
    'optimization.run': 'Ejecutar Optimizacion',
    'optimization.minimizeCost': 'Minimizar Costo',
    'optimization.minimizeRisk': 'Minimizar Riesgo',
    'optimization.maximizeReturn': 'Maximizar Retorno',

    'risk.title': 'Panel de Riesgo',
    'risk.score': 'Puntuacion de Riesgo',
    'risk.var': 'Valor en Riesgo',
    'risk.stress': 'Prueba de Estrés',
    'risk.scenarios': 'Escenarios de Inversion',

    'maturity.title': 'Escalon de Vencimiento de Deuda',
    'maturity.smoothness': 'Suavidad',
    'maturity.walls': 'Muros de Vencimiento',
    'maturity.recommendations': 'Recomendaciones de Refinanciamiento',

    'esg.title': 'Analisis ESG y Bonos Verdes',
    'esg.score': 'Puntuacion ESG',
    'esg.green': 'Elegible Verde',
    'esg.carbon': 'Riesgo de Carbono',
    'esg.climate': 'Calificacion Climatica',

    'ratings.title': 'Simulador de Agencias de Calificacion',
    'ratings.current': 'Calificacion Actual',
    'ratings.simulated': 'Calificacion Simulada',
    'ratings.upgrade': 'Mejora',
    'ratings.downgrade': 'Degradacion',
    'ratings.unchanged': 'Sin Cambio',

    'compliance.title': 'Informes de Cumplimiento FMI',
    'compliance.dsa': 'Analisis de Sostenibilidad de Deuda',
    'compliance.mtds': 'Estrategia de Deuda a Mediano Plazo',
    'compliance.gfs': 'Estadisticas de Finanzas Publicas',

    'security.title': 'Panel de Seguridad',
    'security.score': 'Puntuacion de Seguridad',
    'security.threats': 'Estado de Amenazas',
    'security.users': 'Cuentas de Usuario',

    'auth.login': 'Iniciar Sesion',
    'auth.register': 'Crear Cuenta',
    'auth.email': 'Correo Electronico',
    'auth.password': 'Contrasena',
    'auth.forgotPassword': 'Olvidaste tu contrasena?',
    'auth.noAccount': 'No tienes cuenta?',
    'auth.hasAccount': 'Ya tienes cuenta?',

    'market.yieldCurve': 'Curva de Rendimiento',
    'market.fx': 'Tipos de Cambio',
    'market.rates': 'Tasas de Interes',
    'market.economic': 'Indicadores Economicos',
  },

  fr: {
    'nav.overview': 'Apercu',
    'nav.portfolios': 'Portefeuille de Dette',
    'nav.optimization': 'Optimisation',
    'nav.results': 'Resultats',
    'nav.benchmarks': 'Referentiels',
    'nav.reports': 'Rapports',
    'nav.audit': "Journal d'Audit",
    'nav.market': 'Donnees de Marche',
    'nav.advisor': 'Conseiller IA',
    'nav.peers': 'Pairs',
    'nav.whatif': 'Et Si',
    'nav.riskIntel': 'Intelligence des Risques',
    'nav.risk': 'Tableau de Bord des Risques',
    'nav.compliance': 'Conformite FMI',
    'nav.explain': 'Explicabilite',
    'nav.maturity': 'Echeancier',
    'nav.esg': 'ESG / Vert',
    'nav.ratings': 'Simulateur de Notation',
    'nav.security': 'Securite',
    'nav.status': 'Etat du Systeme',

    'common.loading': 'Chargement...',
    'common.save': 'Enregistrer',
    'common.cancel': 'Annuler',
    'common.delete': 'Supprimer',
    'common.edit': 'Modifier',
    'common.search': 'Rechercher...',
    'common.export': 'Exporter',
    'common.refresh': 'Actualiser',
    'common.noData': 'Aucune donnee disponible',
    'common.total': 'Total',
    'common.actions': 'Actions',
    'common.back': 'Retour',
    'common.next': 'Suivant',
    'common.submit': 'Soumettre',

    'dashboard.title': 'Tableau de Bord',
    'dashboard.welcome': 'Bienvenue sur Quantive',
    'dashboard.portfolios': 'Portefeuilles',
    'dashboard.optimizations': 'Optimisations',
    'dashboard.totalDebt': 'Dette Totale Geree',
    'dashboard.activeJobs': 'Travaux Actifs',

    'portfolio.title': 'Portefeuille de Dette',
    'portfolio.create': 'Creer un Portefeuille',
    'portfolio.name': 'Nom du Portefeuille',
    'portfolio.description': 'Description',
    'portfolio.instruments': 'Instruments',
    'portfolio.totalValue': 'Valeur Totale',
    'portfolio.riskProfile': 'Profil de Risque',

    'optimization.title': "Guide d'Optimisation",
    'optimization.selectPortfolio': 'Selectionner un Portefeuille',
    'optimization.objective': 'Objectif',
    'optimization.constraints': 'Contraintes',
    'optimization.run': 'Lancer Optimisation',
    'optimization.minimizeCost': 'Minimiser le Cout',
    'optimization.minimizeRisk': 'Minimiser le Risque',
    'optimization.maximizeReturn': 'Maximiser le Rendement',

    'risk.title': 'Tableau de Bord des Risques',
    'risk.score': 'Score de Risque',
    'risk.var': 'Valeur a Risque',
    'risk.stress': 'Tests de Stress',
    'risk.scenarios': "Scenarios d'Investissement",

    'maturity.title': 'Echeancier de la Dette',
    'maturity.smoothness': 'Lissage',
    'maturity.walls': "Murs d'Echeance",
    'maturity.recommendations': 'Recommandations de Refinancement',

    'esg.title': 'Analyse ESG et Obligations Vertes',
    'esg.score': 'Score ESG',
    'esg.green': 'Eligibilite Verte',
    'esg.carbon': 'Risque Carbone',
    'esg.climate': 'Classification Climatique',

    'ratings.title': 'Simulateur de Notation',
    'ratings.current': 'Note Actuelle',
    'ratings.simulated': 'Note Simulee',
    'ratings.upgrade': 'Upgrade',
    'ratings.downgrade': 'Downgrade',
    'ratings.unchanged': 'Inchange',

    'compliance.title': 'Rapports de Conformite FMI',
    'compliance.dsa': 'Analyse de Dette Durable',
    'compliance.mtds': 'Strategie de Dette a Moyen Terme',
    'compliance.gfs': 'Statistiques des Finances Publiques',

    'security.title': 'Tableau de Securite',
    'security.score': 'Score de Securite',
    'security.threats': 'Etat des Menaces',
    'security.users': 'Comptes Utilisateurs',

    'auth.login': 'Se Connecter',
    'auth.register': 'Creer un Compte',
    'auth.email': 'E-mail',
    'auth.password': 'Mot de Passe',
    'auth.forgotPassword': 'Mot de passe oublie?',
    'auth.noAccount': "Pas encore de compte?",
    'auth.hasAccount': 'Deja un compte?',

    'market.yieldCurve': 'Courbe des Rendements',
    'market.fx': 'Taux de Change',
    'market.rates': "Taux d'Interet",
    'market.economic': 'Indicateurs Economiques',
  },

  pt: {
    'nav.overview': 'Visao Geral',
    'nav.portfolios': 'Carteira de Divida',
    'nav.optimization': 'Otimizacao',
    'nav.results': 'Resultados',
    'nav.benchmarks': 'Benchmarking',
    'nav.reports': 'Relatorios',
    'nav.audit': 'Registro de Auditoria',
    'nav.market': 'Dados de Mercado',
    'nav.advisor': 'Assessor IA',
    'nav.peers': 'Pares',
    'nav.whatif': 'E Se',
    'nav.riskIntel': 'Inteligencia de Risco',
    'nav.risk': 'Painel de Risco',
    'nav.compliance': 'Conformidade FMI',
    'nav.explain': 'Explicabilidade',
    'nav.maturity': 'Escalonamento de Vencimento',
    'nav.esg': 'ESG / Verde',
    'nav.ratings': 'Simulador de Classificacao',
    'nav.security': 'Seguranca',
    'nav.status': 'Status do Sistema',

    'common.loading': 'Carregando...',
    'common.save': 'Salvar',
    'common.cancel': 'Cancelar',
    'common.delete': 'Excluir',
    'common.edit': 'Editar',
    'common.search': 'Pesquisar...',
    'common.export': 'Exportar',
    'common.refresh': 'Atualizar',
    'common.noData': 'Nenhum dado disponivel',
    'common.total': 'Total',
    'common.actions': 'Acoes',
    'common.back': 'Voltar',
    'common.next': 'Proximo',
    'common.submit': 'Enviar',

    'dashboard.title': 'Painel',
    'dashboard.welcome': 'Bem-vindo ao Quantive',
    'dashboard.portfolios': 'Carteiras',
    'dashboard.optimizations': 'Otimizacoes',
    'dashboard.totalDebt': 'Divida Total Gerenciada',
    'dashboard.activeJobs': 'Trabalhos Ativos',

    'portfolio.title': 'Carteira de Divida',
    'portfolio.create': 'Criar Carteira',
    'portfolio.name': 'Nome da Carteira',
    'portfolio.description': 'Descricao',
    'portfolio.instruments': 'Instrumentos',
    'portfolio.totalValue': 'Valor Total',
    'portfolio.riskProfile': 'Perfil de Risco',

    'optimization.title': 'Assistente de Otimizacao',
    'optimization.selectPortfolio': 'Selecionar Carteira',
    'optimization.objective': 'Objetivo',
    'optimization.constraints': 'Restricoes',
    'optimization.run': 'Executar Otimizacao',
    'optimization.minimizeCost': 'Minimizar Custo',
    'optimization.minimizeRisk': 'Minimizar Risco',
    'optimization.maximizeReturn': 'Maximizar Retorno',

    'risk.title': 'Painel de Risco',
    'risk.score': 'Pontuacao de Risco',
    'risk.var': 'Valor em Risco',
    'risk.stress': 'Teste de Estresse',
    'risk.scenarios': 'Cenarios de Investimento',

    'maturity.title': 'Escalonamento de Vencimento da Divida',
    'maturity.smoothness': 'Suavidade',
    'maturity.walls': 'Muros de Vencimento',
    'maturity.recommendations': 'Recomendacoes de Refinanciamento',

    'esg.title': 'Analise ESG e Titulos Verdes',
    'esg.score': 'Pontuacao ESG',
    'esg.green': 'Elegibilidade Verde',
    'esg.carbon': 'Risco de Carbono',
    'esg.climate': 'Classificacao Climatica',

    'ratings.title': 'Simulador de Classificacao',
    'ratings.current': 'Classificacao Atual',
    'ratings.simulated': 'Classificacao Simulada',
    'ratings.upgrade': 'Upgrade',
    'ratings.downgrade': 'Downgrade',
    'ratings.unchanged': 'Sem Mudanca',

    'compliance.title': 'Relatorios de Conformidade FMI',
    'compliance.dsa': 'Analise de Sustentabilidade da Divida',
    'compliance.mtds': 'Estrategia de Divida de Médio Prazo',
    'compliance.gfs': 'Estatisticas de Financas Publicas',

    'security.title': 'Painel de Seguranca',
    'security.score': 'Pontuacao de Seguranca',
    'security.threats': 'Status de Ameacas',
    'security.users': 'Contas de Usuarios',

    'auth.login': 'Entrar',
    'auth.register': 'Criar Conta',
    'auth.email': 'E-mail',
    'auth.password': 'Senha',
    'auth.forgotPassword': 'Esqueceu a senha?',
    'auth.noAccount': 'Nao tem conta?',
    'auth.hasAccount': 'Ja tem conta?',

    'market.yieldCurve': 'Curva de Rendimento',
    'market.fx': 'Taxas de Cambio',
    'market.rates': 'Taxas de Juros',
    'market.economic': 'Indicadores Economicos',
  },
};

// ── Context + Hook ───────────────────────────────────────────────────
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
  availableLocales: Locale[];
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    try {
      return (localStorage.getItem('quantive_locale') as Locale) || 'en';
    } catch {
      return 'en';
    }
  });

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try { localStorage.setItem('quantive_locale', l); } catch { /* noop */ }
  }, []);

  const t = useCallback((key: string): string => {
    return translations[locale]?.[key] || translations.en[key] || key;
  }, [locale]);

  return (
    <I18nContext.Provider value={{ locale, setLocale, t, availableLocales: ['en', 'es', 'fr', 'pt'] }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used within I18nProvider');
  return ctx;
}

export { translations };
