import React from 'react';
import { del } from 'idb-keyval';

export default function ErrorPage({ statusCode = 404, onHome }) {
    const handleHome = () => {
        // 모든 상태 초기화
        sessionStorage.removeItem('appState');
        del('uploadedFile').catch(() => {});

        if (onHome) {
            onHome();
        } else {
            window.location.href = '/';
        }
    };

    const errorDetails = {
        404: {
            title: '404',
            subtitle: '페이지를 찾을 수 없습니다',
            icon: '🔍',
            description: '요청하신 페이지가 존재하지 않거나 삭제되었을 수 있습니다.',
            suggestions: [
                '입력하신 URL을 다시 확인해주세요',
                '홈페이지로 돌아가 다시 시도해주세요',
                '메뉴를 통해 원하는 페이지를 찾아보세요'
            ],
            color: 'from-blue-500 to-blue-600'
        },
        500: {
            title: '500',
            subtitle: '서버에 오류가 발생했습니다',
            icon: '⚙️',
            description: '일시적인 서버 문제로 요청을 처리할 수 없습니다.',
            suggestions: [
                '잠시 후 다시 시도해주세요',
                '브라우저를 새로고침(F5)해주세요',
                '문제가 계속되면 메일로 이슈를 알려주세요.'
            ],
            color: 'from-red-500 to-red-600'
        },
        400: {
            title: '400',
            subtitle: '잘못된 요청입니다',
            icon: '❌',
            description: '요청 형식이 올바르지 않아 처리할 수 없습니다.',
            suggestions: [
                '입력하신 정보를 확인해주세요',
                '필수 항목을 모두 입력했는지 확인하세요',
                '올바른 형식으로 다시 입력해주세요'
            ],
            color: 'from-yellow-500 to-yellow-600'
        }
    };

    const error = errorDetails[statusCode] || errorDetails[404];

    return (
        <div className={`flex items-center justify-center min-h-screen bg-gradient-to-br ${error.color}`}>
            <div className="w-full max-w-md mx-auto px-6 py-12">
                {/* 카드 컨테이너 */}
                <div className="bg-white rounded-2xl shadow-2xl p-8 md:p-12">
                    {/* 아이콘 */}
                    <div className="text-center mb-6">
                        <div className="text-6xl mb-3 animate-bounce">
                            {error.icon}
                        </div>
                    </div>

                    {/* 오류 코드 */}
                    <div className="text-center mb-5">
                        <h1 className="text-4xl font-extrabold text-gray-800 mb-2">
                            {error.title}
                        </h1>
                        <p className="text-xl font-bold text-gray-600">
                            {error.subtitle}
                        </p>
                    </div>

                    {/* 오류 설명 */}
                    <p className="text-gray-600 text-center mb-6 leading-relaxed text-sm">
                        {error.description}
                    </p>

                    {/* 해결 방법 */}
                    <div className="bg-gray-50 rounded-lg p-5 mb-6">
                        <h3 className="font-bold text-gray-800 mb-3 text-xs uppercase tracking-wide">
                            어떻게 해야 하나요?
                        </h3>
                        <ul className="space-y-2">
                            {error.suggestions.map((suggestion, index) => (
                                <li key={index} className="flex items-start gap-2">
                                    <span className="text-blue-600 font-bold text-sm flex-shrink-0">✓</span>
                                    <span className="text-gray-700 text-xs">{suggestion}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* 버튼 그룹 */}
                    <div className="flex flex-col gap-2">
                        <button
                            onClick={handleHome}
                            className="w-full px-6 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-bold rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all shadow-lg hover:shadow-xl text-sm"
                        >
                            🏠 홈으로 돌아가기
                        </button>
                    </div>

                    {/* 지원 정보 */}
                    <div className="mt-6 pt-6 border-t border-gray-200">
                        <p className="text-center text-gray-500 text-xs">
                            문제가 계속되거나 도움이 필요하신가요?
                        </p>
                        <p className="text-center mt-2">
                            <a 
                                href="mailto:support@easywelfare.com" 
                                className="text-blue-600 hover:underline font-semibold text-xs"
                            >
                                문의하기
                            </a>
                        </p>
                    </div>
                </div>

                {/* 하단 데코레이션*/}
                <div className="text-center mt-8 text-white opacity-75">
                    <p className="text-sm">이음:새 - 복잡한 공공문서를 가깝게</p>
                </div>
            </div>
        </div>
    );
}
