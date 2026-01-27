import React, { useState } from 'react';
import characterImage from '../../assets/images/service_intro_character.png';
import teamImage from '../../assets/images/team_members.png';
import CloseIcon from '@mui/icons-material/Close';
import AutoStoriesIcon from '@mui/icons-material/AutoStories';
import GroupsIcon from '@mui/icons-material/Groups';

export default function ServiceIntroModal({ isOpen, onClose }) {
    const [activeTab, setActiveTab] = useState('intro');

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            ></div>

            {/* Modal Content */}
            <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-fade-in-up flex flex-col max-h-[90vh]">

                {/* Header (Tabs) */}
                <div className="bg-gray-50 border-b border-gray-100 p-2 flex gap-2">
                    <button
                        onClick={() => setActiveTab('intro')}
                        className={`flex-1 py-3 rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2
                        ${activeTab === 'intro'
                                ? 'bg-white text-gray-800 shadow-sm ring-1 ring-black/5'
                                : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'}`}
                    >
                        <AutoStoriesIcon sx={{ fontSize: 18 }} />
                        [이음:새] 소개
                    </button>
                    <button
                        onClick={() => setActiveTab('team')}
                        className={`flex-1 py-3 rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2
                        ${activeTab === 'team'
                                ? 'bg-white text-gray-800 shadow-sm ring-1 ring-black/5'
                                : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'}`}
                    >
                        <GroupsIcon sx={{ fontSize: 18 }} />
                        만든 사람들
                    </button>

                    {/* Close Button (Absolute to top right of header) */}
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 z-10"
                    >
                        <CloseIcon />
                    </button>
                </div>

                {/* Body Content */}
                <div className="p-8 overflow-y-auto">
                    {activeTab === 'intro' && (
                        <div className="space-y-6">
                            <div className="text-center mb-8">
                                <img src={characterImage} alt="Character" className="w-48 mx-auto mb-4 drop-shadow-md" />
                                <h2 className="text-2xl font-bold text-gray-800 mb-3 leading-tight">
                                    "복잡한 공공문서를 가볍게,<br />설명은 쉽고 가깝게"
                                </h2>
                                <p className="text-gray-500 text-sm italic bg-gray-50 py-3 px-4 rounded-lg inline-block">
                                    사회초년생 A씨의 막막했던 마음을<br />떠올리며 꼼꼼하게 만들었습니다.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 gap-4">
                                <FeatureBox
                                    title="OCR (이미지 인식)"
                                    desc="종이 문서를 찍기만 하세요. 텍스트로 변환해 분석합니다."
                                    color="blue"
                                />
                                <FeatureBox
                                    title="눈높이 설명"
                                    desc="어려운 행정 용어를 쉬운 말로 풀어서 설명해드립니다."
                                    color="green"
                                />
                                <FeatureBox
                                    title="RAG (근거 기반 요약)"
                                    desc="문서의 내용을 정확하게 근거하여 핵심만 요약합니다."
                                    color="purple"
                                />
                            </div>
                        </div>
                    )}

                    {activeTab === 'team' && (
                        <div className="text-center py-4">
                            <div className="mb-10">
                                <h2 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 mb-2">
                                    이레라 (Erera)
                                </h2>
                                <p className="text-gray-500 font-medium">
                                    "이해의 틈을 이어, 삶을 레벨업하다"
                                </p>
                            </div>

                            <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100 mb-10">
                                <h3 className="text-2xl font-bold text-gray-400 uppercase tracking-widest mb-6">TEAM MEMBERS</h3>
                                <img src={teamImage} alt="Team" className="w-full max-w-2xl mx-auto mb-6 rounded-lg drop-shadow-sm" />
                                <div className="flex flex-col gap-3 justify-center items-center">
                                    <div className="flex justify-center gap-3">
                                        <MemberBadge name="박나은" />
                                        <MemberBadge name="김현식" />
                                        <MemberBadge name="김은선" />
                                    </div>
                                    <div className="flex justify-center gap-3">
                                        <MemberBadge name="윤여은" />
                                        <MemberBadge name="김문정" />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-gray-50 flex justify-center bg-gray-50/50">
                    <button
                        onClick={onClose}
                        className="px-8 py-2.5 bg-gray-900 text-white rounded-full text-sm font-bold hover:bg-black transition-colors shadow-lg shadow-gray-200"
                    >
                        닫기
                    </button>
                </div>
            </div>
        </div>
    );
}

function FeatureBox({ title, desc, color }) {
    const colorMap = {
        blue: 'bg-blue-50 text-blue-700 border-blue-100',
        green: 'bg-green-50 text-green-700 border-green-100',
        purple: 'bg-purple-50 text-purple-700 border-purple-100'
    };

    return (
        <div className={`p-4 rounded-xl border ${colorMap[color]} text-left transition-transform hover:scale-[1.02]`}>
            <h3 className="font-bold text-sm mb-1">{title}</h3>
            <p className="text-xs opacity-80 leading-relaxed">{desc}</p>
        </div>
    );
}

function MemberBadge({ name }) {
    return (
        <span className="bg-white border border-gray-200 text-gray-700 px-4 py-2 rounded-full text-sm font-bold shadow-sm hover:shadow-md transition-all hover:text-blue-600 hover:border-blue-200 cursor-default">
            {name}
        </span>
    );
}
