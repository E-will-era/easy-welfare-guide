 
   export default function ServiceReference({ references }) {
    return (
        <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-sm text-blue-800 mb-2">
                더 자세한 정보는 아래 링크에서 확인하세요
            </p>
            <div className="flex flex-col gap-2">
                {(!references || references.length === 0) ? (
                    <span className="text-sm text-gray-500">DB에서 관련 정보를 찾을 수 없습니다.</span>
                ) : (
                    references.map((ref, idx) => (
                        <a
                            key={idx}
                            href={ref.resource}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline text-sm break-all"
                        >
                            {ref.title}
                        </a>
                    ))
                )}
            </div>
        </div>
     );
}
