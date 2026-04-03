import MainPage from './pages/MainPage';
import ErrorPage from './pages/ErrorPage';
import { useState } from 'react';
import { del } from 'idb-keyval';

function App() {
  const [error, setError] = useState(null); // { statusCode: 400|404|500 }

  const handleError = (statusCode) => {
    // 에러 발생 시 저장된 상태 클리어 (새로고침하면 초기 상태로)
    sessionStorage.removeItem('appState');
    del('uploadedFile').catch(() => {});
    setError({ statusCode });
  };

  const handleClearError = () => {
    setError(null);
  };

  if (error) {
    return (
      <ErrorPage
        statusCode={error.statusCode}
        onHome={handleClearError}
      />
    );
  }

  return (
    <div className="App">
      <MainPage onError={handleError} />
    </div>
  );
}

export default App;
