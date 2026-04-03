import React from 'react';
import {
    Paper,
    Box,
    Typography,
    Button,
    Chip,
    CircularProgress,
    Divider,
} from '@mui/material';
import ArticleIcon from '@mui/icons-material/Article';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import PlaceIcon from '@mui/icons-material/Place';
import PhoneIcon from '@mui/icons-material/Phone';

/**
 * 설명: 복지 신청 프로그램에 필요한 서류 목록 카드를 안내하고 화면에 표시하는 컴포넌트 유닛.
 * 작동 방식: 발급기관, 안내문, 이름 등이 들어간 서류 배열 객체를 리스트화. 하단엔 신청 도움 팁도 기록.
 * 반환값: 문서가이드가 레이아웃 구조화 되어 정리된 MUI Paper 출력물.
 */
export default function DocumentGuideCard({ documents, loading }) {

    // 문서 가이드를 백엔드 서버에서 가져와 조회하는 동안의 로딩 표출 스피너
    if (loading) {
        return (
            <Paper
                elevation={0}
                sx={{
                    borderRadius: '16px',
                    p: { xs: 3, sm: 4 },
                    bgcolor: 'rgba(255,255,255,0.95)',
                    border: '2px solid #bfdbfe',
                    boxShadow: '0 4px 20px -4px rgba(59, 130, 246, 0.15)',
                }}
            >
                <Box className="flex flex-col items-center py-6 gap-3">
                    <CircularProgress size={36} sx={{ color: '#3b82f6' }} />
                    <Typography variant="body2" sx={{ color: '#6b7280' }}>
                        서류 안내를 불러오는 중입니다...
                    </Typography>
                </Box>
            </Paper>
        );
    }

    // 화면에 보여줄 문서 객체가 아예 없을 시 컴포넌트 마운트 종료
    if (!documents) return null;

    const { program_name, documents: docList = [], application_info, tips = [] } = documents;

    return (
        <Paper
            elevation={0}
            sx={{
                borderRadius: '16px',
                p: { xs: 3, sm: 4 },
                bgcolor: 'rgba(255,255,255,0.95)',
                border: '2px solid #bfdbfe',
                boxShadow: '0 4px 20px -4px rgba(59, 130, 246, 0.15)',
            }}
        >
            {/* Card Header */}
            <Box className="flex items-center gap-2 mb-1">
                <ArticleIcon sx={{ color: '#3b82f6', fontSize: 24 }} />
                <Typography
                    variant="h6"
                    sx={{ fontWeight: 700, color: '#1e3a5f', fontSize: '1.1rem' }}
                >
                    필요 서류 안내
                </Typography>
            </Box>

            {/* Optional program name subtitle */}
            {program_name && (
                <Typography
                    variant="body2"
                    sx={{ color: '#6b7280', mb: 3, ml: '32px' }}
                >
                    {program_name}
                </Typography>
            )}

            {!program_name && <Box sx={{ mb: 3 }} />}

            {/* Document list */}
            {docList.length > 0 ? (
                <Box className="flex flex-col gap-3">
                    {docList.map((doc, index) => (
                        <DocumentItem key={index} doc={doc} />
                    ))}
                </Box>
            ) : (
                <Typography variant="body2" sx={{ color: '#9ca3af', mb: 3 }}>
                    서류 정보가 없습니다.
                </Typography>
            )}

            {/* Tips section */}
            {tips.length > 0 && (
                <>
                    <Divider sx={{ my: 3, borderColor: '#e5e7eb' }} />
                    <Box>
                        <Box className="flex items-center gap-2 mb-2">
                            <LightbulbIcon sx={{ color: '#f59e0b', fontSize: 20 }} />
                            <Typography
                                variant="body2"
                                sx={{ fontWeight: 700, color: '#92400e' }}
                            >
                                신청 팁
                            </Typography>
                        </Box>
                        <Box
                            sx={{
                                bgcolor: '#fffbeb',
                                border: '1px solid #fde68a',
                                borderRadius: '10px',
                                p: 2,
                            }}
                        >
                            {tips.map((tip, index) => (
                                <Typography
                                    key={index}
                                    variant="body2"
                                    sx={{ color: '#78350f', lineHeight: 1.7 }}
                                >
                                    - {tip}
                                </Typography>
                            ))}
                        </Box>
                    </Box>
                </>
            )}

            {/* Application info: location and contact */}
            {application_info && (application_info.where_to_apply || application_info.contact) && (
                <>
                    <Divider sx={{ my: 3, borderColor: '#e5e7eb' }} />
                    <Box className="flex flex-col gap-2">
                        {application_info.where_to_apply && (
                            <Box className="flex items-start gap-2">
                                <PlaceIcon sx={{ color: '#6b7280', fontSize: 18, mt: '2px', flexShrink: 0 }} />
                                <Typography variant="body2" sx={{ color: '#374151' }}>
                                    <strong>신청 장소:</strong> {application_info.where_to_apply}
                                </Typography>
                            </Box>
                        )}
                        {application_info.contact && (
                            <Box className="flex items-start gap-2">
                                <PhoneIcon sx={{ color: '#6b7280', fontSize: 18, mt: '2px', flexShrink: 0 }} />
                                <Typography variant="body2" sx={{ color: '#374151' }}>
                                    <strong>문의:</strong> {application_info.contact}
                                </Typography>
                            </Box>
                        )}
                    </Box>
                </>
            )}
        </Paper>
    );
}

/**
 * 설명: 카드 목록내의 단일 정보 문서 서류 아이템 항목에 대한 렌더러 처리 모듈.
 * 작동 방식: 온라인 발급 링크 등을 통해 정부 발급 도메인을 붙여서 제공.
 * 반환값: 문서 구체적 데이터가 포함되어 시각적으로 구조화된 렌더링 Box.
 */
function DocumentItem({ doc }) {
    const {
        doc_name: name,
        issuer,
        description,
        online_url,
        is_required,
    } = doc;

    /**
     * 설명: 주소표출 URL 정보를 브라우저 탭에 안전하게 새 오픈으로 띄워주는 트리거 함수.
     * 작동 방식: noopener와 noreferrer 속성 인자들을 덧붙여 브라우저 보안 이슈를 방지.
     * 반환값: void
     */
    const handleOpenLink = () => {
        if (online_url) {
            window.open(online_url, '_blank', 'noopener,noreferrer');
        }
    };

    return (
        <Box
            sx={{
                borderRadius: '12px',
                p: { xs: 2, sm: 2.5 },
                bgcolor: '#f8fafc',
                border: '1px solid #e2e8f0',
                transition: 'box-shadow 0.2s',
                '&:hover': {
                    boxShadow: '0 2px 8px -2px rgba(59, 130, 246, 0.15)',
                },
            }}
        >
            {/* Document name row with optional required badge */}
            <Box className="flex items-center gap-2 mb-1 flex-wrap">
                <ArticleIcon sx={{ color: '#64748b', fontSize: 18, flexShrink: 0 }} />
                <Typography
                    variant="body2"
                    sx={{ fontWeight: 700, color: '#1e293b', fontSize: '0.95rem' }}
                >
                    {name}
                </Typography>
                {is_required && (
                    <Chip
                        label="필수"
                        size="small"
                        sx={{
                            bgcolor: '#fee2e2',
                            color: '#b91c1c',
                            fontWeight: 700,
                            fontSize: '0.7rem',
                            height: 20,
                            border: '1px solid #fecaca',
                        }}
                    />
                )}
            </Box>

            {/* Issuer */}
            {issuer && (
                <Typography
                    variant="body2"
                    sx={{ color: '#64748b', fontSize: '0.82rem', mb: description ? 0.5 : 0, ml: '26px' }}
                >
                    발급처: {issuer}
                </Typography>
            )}

            {/* Description */}
            {description && (
                <Typography
                    variant="body2"
                    sx={{ color: '#475569', fontSize: '0.82rem', ml: '26px', mb: online_url ? 1.5 : 0 }}
                >
                    {description}
                </Typography>
            )}

            {/* Online issuance link button — only shown when online_url is provided */}
            {online_url && (
                <Box sx={{ ml: '26px', mt: description ? 0 : 1.5 }}>
                    <Button
                        variant="outlined"
                        size="small"
                        onClick={handleOpenLink}
                        endIcon={<OpenInNewIcon sx={{ fontSize: '14px !important' }} />}
                        sx={{
                            borderRadius: '8px',
                            textTransform: 'none',
                            fontWeight: 600,
                            fontSize: '0.8rem',
                            py: 0.5,
                            px: 1.5,
                            borderColor: '#3b82f6',
                            color: '#3b82f6',
                            '&:hover': {
                                borderColor: '#1d4ed8',
                                bgcolor: '#eff6ff',
                            },
                        }}
                    >
                        온라인 발급 바로가기
                    </Button>
                </Box>
            )}
        </Box>
    );
}
