import MainPage from './pages/MainPage';
import ErrorPage from './pages/ErrorPage';
import { useState } from 'react';

function App() {
  // 초기 상태에서 오류 페이지 표시
  const [showError, setShowError] = useState(true);
  const [errorCode, setErrorCode] = useState(404);

  const handleShowError = (code) => {
    setErrorCode(code);
    setShowError(true);
  };

  if (showError) {
    return (
      <div>
        <ErrorPage statusCode={errorCode} />
        <button
          onClick={() => setShowError(false)}
          className="fixed top-4 left-4 px-4 py-2 bg-white text-blue-600 font-bold rounded-lg shadow-lg hover:bg-gray-100 z-50"
        >
          ← 메인으로
        </button>
        {/* 다른 오류 테스트 버튼 */}
        <div className="fixed bottom-4 left-4 space-y-2 z-50">
          {errorCode !== 404 && (
            <button
              onClick={() => handleShowError(404)}
              className="block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              404 오류 보기
            </button>
          )}
          {errorCode !== 500 && (
            <button
              onClick={() => handleShowError(500)}
              className="block px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 text-sm"
            >
              500 오류 보기
            </button>
          )}
          {errorCode !== 400 && (
            <button
              onClick={() => handleShowError(400)}
              className="block px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm"
            >
              400 오류 보기
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <MainPage />
      {/* 오류 테스트 버튼 */}
      <button
        onClick={() => handleShowError(404)}
        className="fixed bottom-4 right-4 px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-900 text-sm opacity-50 hover:opacity-100 z-50"
      >
        🔍 오류 페이지 테스트
      </button>
    </div>
  );
}
export default App;
