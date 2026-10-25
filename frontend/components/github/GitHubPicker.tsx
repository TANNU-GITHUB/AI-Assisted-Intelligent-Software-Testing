'use client';

import { useEffect, useState } from 'react';
import { Folder, FileCode2, FileText, Github, Loader2, Unplug } from 'lucide-react';
import {
  disconnectGitHub,
  fetchGitHubStatus,
  getGitHubAuthUrl,
  type GitHubProfile,
} from '@/lib/auth';
import {
  importFromGitHub,
  listGitHubContents,
  listGitHubRepos,
  type GitHubEntry,
  type GitHubRepo,
} from '@/lib/api';

type Props = {
  disabled?: boolean;
  onImported: (payload: {
    filename: string;
    source_code: string;
    requirements_text: string;
  }) => void;
};

export function GitHubPicker({ disabled, onImported }: Props) {
  const [status, setStatus] = useState<GitHubProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(false);
  const [selected, setSelected] = useState<GitHubRepo | null>(null);
  const [path, setPath] = useState('');
  const [entries, setEntries] = useState<GitHubEntry[]>([]);
  const [sourcePath, setSourcePath] = useState<string | null>(null);
  const [reqPath, setReqPath] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);

  useEffect(() => {
    fetchGitHubStatus()
      .then(setStatus)
      .catch(() => setStatus({ connected: false }));
  }, []);

  useEffect(() => {
    if (!status?.connected) return;
    setLoadingRepos(true);
    listGitHubRepos()
      .then((data) => setRepos(data.repos))
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load repositories.'))
      .finally(() => setLoadingRepos(false));
  }, [status?.connected]);

  useEffect(() => {
    if (!selected) return;
    listGitHubContents(selected.owner, selected.name, path)
      .then((data) => setEntries(data.entries))
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not list files.'));
  }, [selected, path]);

  async function connect() {
    setError(null);
    setConnecting(true);
    try {
      const { url, state } = await getGitHubAuthUrl();
      sessionStorage.setItem('bugai_github_oauth_state', state);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'GitHub is not configured.');
      setConnecting(false);
    }
  }

  async function disconnect() {
    setError(null);
    await disconnectGitHub();
    setStatus({ connected: false });
    setRepos([]);
    setSelected(null);
    setSourcePath(null);
    setReqPath(null);
  }

  async function importSelected() {
    if (!selected || !sourcePath) return;
    setImporting(true);
    setError(null);
    try {
      const data = await importFromGitHub({
        owner: selected.owner,
        repo: selected.name,
        source_path: sourcePath,
        requirements_path: reqPath,
      });
      onImported({
        filename: data.filename,
        source_code: data.source_code,
        requirements_text: data.requirements_text,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed.');
    } finally {
      setImporting(false);
    }
  }

  const crumbs = path ? path.split('/').filter(Boolean) : [];

  return (
    <div className="max-w-7xl mx-auto mb-4 rounded-2xl border border-neutral-800 bg-neutral-950 p-4">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <Github className="w-4 h-4 text-yellow-500" />
        <span className="font-mono text-xs text-neutral-400 tracking-wider">GITHUB REPOS</span>
        {status?.connected ? (
          <>
            <span className="text-xs text-neutral-300">
              Connected as <span className="text-yellow-500">{status.login}</span>
            </span>
            <button
              type="button"
              onClick={disconnect}
              disabled={disabled}
              className="ml-auto flex items-center gap-1 text-xs text-neutral-500 hover:text-white"
            >
              <Unplug className="w-3 h-3" />
              Disconnect
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={connect}
            disabled={disabled || connecting}
            className="ml-auto text-xs font-medium px-3 py-1.5 rounded-full bg-yellow-500 text-black hover:bg-yellow-400"
          >
            {connecting ? 'Opening GitHub…' : 'Connect GitHub'}
          </button>
        )}
      </div>

      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}

      {!status?.connected && (
        <p className="text-xs text-neutral-500">
          Grant access to your GitHub repositories, then pick a Python file (and optional requirements
          text) to load into Live Lab.
        </p>
      )}

      {status?.connected && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-xl border border-neutral-800 p-3 max-h-56 overflow-auto">
            {loadingRepos ? (
              <div className="flex items-center gap-2 text-xs text-neutral-500">
                <Loader2 className="w-3 h-3 animate-spin" /> Loading repositories…
              </div>
            ) : (
              <ul className="space-y-1">
                {repos.map((repo) => (
                  <li key={repo.id}>
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => {
                        setSelected(repo);
                        setPath('');
                        setSourcePath(null);
                        setReqPath(null);
                      }}
                      className={`w-full text-left px-2 py-1.5 rounded-lg text-xs ${
                        selected?.id === repo.id
                          ? 'bg-yellow-500/15 text-yellow-500'
                          : 'text-neutral-300 hover:bg-neutral-900'
                      }`}
                    >
                      <span className="font-mono">{repo.full_name}</span>
                      {repo.private && (
                        <span className="ml-2 text-[10px] text-neutral-500">private</span>
                      )}
                    </button>
                  </li>
                ))}
                {repos.length === 0 && (
                  <li className="text-xs text-neutral-500">No repositories returned.</li>
                )}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-neutral-800 p-3 max-h-56 overflow-auto">
            {!selected ? (
              <p className="text-xs text-neutral-500">Select a repository to browse files.</p>
            ) : (
              <>
                <div className="flex flex-wrap gap-1 mb-2 text-[11px] font-mono text-neutral-500">
                  <button type="button" onClick={() => setPath('')} className="hover:text-yellow-500">
                    {selected.full_name}
                  </button>
                  {crumbs.map((part, index) => {
                    const next = crumbs.slice(0, index + 1).join('/');
                    return (
                      <span key={next}>
                        /
                        <button
                          type="button"
                          onClick={() => setPath(next)}
                          className="hover:text-yellow-500 ml-1"
                        >
                          {part}
                        </button>
                      </span>
                    );
                  })}
                </div>
                <ul className="space-y-1">
                  {path && (
                    <li>
                      <button
                        type="button"
                        className="text-xs text-neutral-400 hover:text-white"
                        onClick={() => setPath(path.split('/').slice(0, -1).join('/'))}
                      >
                        ..
                      </button>
                    </li>
                  )}
                  {entries.map((entry) => (
                    <li key={entry.path}>
                      {entry.type === 'dir' ? (
                        <button
                          type="button"
                          onClick={() => setPath(entry.path)}
                          className="flex items-center gap-2 w-full text-left text-xs text-neutral-300 hover:text-white"
                        >
                          <Folder className="w-3 h-3 text-yellow-500" />
                          {entry.name}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => {
                            if (entry.kind === 'source') setSourcePath(entry.path);
                            else setReqPath(entry.path);
                          }}
                          className={`flex items-center gap-2 w-full text-left text-xs ${
                            sourcePath === entry.path || reqPath === entry.path
                              ? 'text-yellow-500'
                              : 'text-neutral-300 hover:text-white'
                          }`}
                        >
                          {entry.kind === 'source' ? (
                            <FileCode2 className="w-3 h-3" />
                          ) : (
                            <FileText className="w-3 h-3" />
                          )}
                          {entry.name}
                          {sourcePath === entry.path && (
                            <span className="ml-auto text-[10px]">source</span>
                          )}
                          {reqPath === entry.path && (
                            <span className="ml-auto text-[10px]">requirements</span>
                          )}
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </div>
      )}

      {status?.connected && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <p className="text-[11px] text-neutral-500">
            Source: {sourcePath || 'pick a .py file'} · Requirements: {reqPath || 'optional .txt/.md'}
          </p>
          <button
            type="button"
            disabled={disabled || !sourcePath || importing}
            onClick={importSelected}
            className="ml-auto text-xs font-medium px-3 py-1.5 rounded-full bg-yellow-500 text-black hover:bg-yellow-400 disabled:opacity-40"
          >
            {importing ? 'Importing…' : 'Load into Live Lab'}
          </button>
        </div>
      )}
    </div>
  );
}
